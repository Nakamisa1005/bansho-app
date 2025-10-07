import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import vision
import google.generativeai as genai
import pyrebase # Pyrebaseをインポート
from dotenv import load_dotenv

load_dotenv()

# --- Flaskアプリケーションの準備 ---
app = Flask(__name__)
# ▼▼▼【修正点1】セッション機能のために秘密鍵を設定▼▼▼
app.secret_key = 'a-very-secret-and-random-key' # この文字列は何でも良いですが、秘密にしてください

# --- 各種設定 ---
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ▼▼▼【修正点2】Firebase Authentication (Pyrebase) の設定を追加▼▼▼
firebaseConfig = {
  "apiKey": "AIzaSyBYosHPBYGwbA7rKSNEUqNKVB4MRhuz90c",
  "authDomain": "bansho-app.firebaseapp.com",
  "projectId": "bansho-app",
  "storageBucket": "bansho-app.firebasestorage.app",
  "messagingSenderId": "61635968086",
  "appId": "1:61635968086:web:6e18b7ee4236f359bbcff7",
  "databaseURL": ""
}
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth() # 認証用のauthオブジェクト

# --- Firebase Admin SDK (Firestore) の設定 ---
firebase_cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
if firebase_cred_path:
    # 既に初期化されているかチェック
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print("Firebaseの認証情報(環境変数)が見つかりません。")

# --- Gemini APIキーの設定 ---
gemini_api_key = os.environ.get('GEMINI_API_KEY')
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    print("Gemini APIキー(環境変数)が見つかりません。")

# ==============================================================================
# 関数たち（部品）
# ==============================================================================
# ... (detect_text_with_vision_api と generate_study_content_from_text は変更なし) ...
def detect_text_with_vision_api(image_path):
    client = vision.ImageAnnotatorClient()
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    if response.error.message:
        raise Exception(response.error.message)
    return response.full_text_annotation.text

def generate_study_content_from_text(text):
    model = genai.GenerativeModel('gemini-pro-latest')
    prompt = f"""
    あなたは優秀な学習アシスタントです。
    以下のテキストは、学生が撮影したノートや板書の一部です。
    このテキストから、学生が復習しやすいように以下の3つの要素を抽出・生成してください。
    会話や前置き、冒頭の挨拶は一切不要です。

    # 生成する項目
    1. **要点まとめ**: テキスト全体の内容を箇条書きで簡潔にまとめる。
    2. **重要キーワード**: 重要だと思われる単語を3〜5個挙げる。
    3. **復習問題**: 「穴埋め」「選択」「記述」の問題形式をバランス良く織り交ぜる。

    # 復習問題の形式
    TYPE:穴埋め@@QUESTION:(問題文。空欄は〇〇と記述)@@ANSWER:(答え)
    TYPE:選択@@QUESTION:(問題文)@@CHOICES:(選択肢1),(選択肢2),(選択肢3)@@ANSWER:(答え)
    TYPE:記述@@QUESTION:(問題文)@@ANSWER:(模範解答の要点やキーワード)

    ---
    【元のテキスト】
    {text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        return response.text.replace('•', '  *')
    except Exception as e:
        return f"AI処理中にエラー: {e}"

# ==============================================================================
# 認証ルート (ログイン・サインアップ) - (このセクションは変更なし)
# ==============================================================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            auth.create_user_with_email_and_password(email, password)
            flash('新規登録が成功しました。ログインしてください。', 'success')
            return redirect(url_for('login'))
        except Exception:
            flash('登録に失敗しました。このメールアドレスは既に使用されている可能性があります。', 'danger')
            return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = user['idToken']
            flash('ログインしました。', 'success')
            return redirect(url_for('home'))
        except Exception:
            flash('メールアドレスまたはパスワードが間違っています。', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))

# ==============================================================================
# Flaskのルーティング（Webページの各URLの処理）
# ==============================================================================
@app.route('/')
def home():
    if 'user' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_and_process():
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))
    
    if 'image' not in request.files: return "エラー: ファイルが選択されていません。"
    file = request.files['image']
    if file.filename == '': return "エラー: ファイル名が空です。"
    
    if file:
        tag = request.form.get('tag', '未分類')
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            extracted_text = detect_text_with_vision_api(filepath)
            final_result = generate_study_content_from_text(extracted_text)
            db.collection('notes').add({
                'user_id': user_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'ocr_text': extracted_text,
                'ai_result': final_result,
                'tag': tag
            })
            # ... (クイズ解析部分は省略)
            return render_template('result.html', extracted_text_data=extracted_text, result_text=final_result, quizzes=[])
        except Exception as e:
            return f"処理中にエラーが発生しました: {e}"
    return "エラー: 不明なエラーが発生しました。"

@app.route('/archive')
def archive_tags():
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))

    # ▼▼▼【修正点3】重複したクエリを削除し、ユーザーIDでの絞り込みを正しく行う▼▼▼
    notes_ref = db.collection('notes').where('user_id', '==', user_id).stream()
    
    tags = set()
    for note in notes_ref:
        note_data = note.to_dict()
        if 'tag' in note_data:
            tags.add(note_data['tag'])
    return render_template('archive_tags.html', tags=sorted(list(tags)))

@app.route('/archive/<tag_name>')
def archive_by_tag(tag_name):
    # ▼▼▼【修正点4】セキュリティチェックを追加▼▼▼
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))
    
    notes_ref = db.collection('notes').where('user_id', '==', user_id).where('tag', '==', tag_name).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    
    notes_list = []
    for note in notes_ref:
        note_data = note.to_dict()
        note_data['id'] = note.id
        notes_list.append(note_data)
    return render_template('archive.html', notes=notes_list, tag_name=tag_name)

@app.route('/note/<note_id>')
def edit_note(note_id):
    # ▼▼▼【修正点4】セキュリティチェックを追加▼▼▼
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))
        
    note_ref = db.collection('notes').document(note_id).get()
    if note_ref.exists:
        note_data = note_ref.to_dict()
        # ★★★自分のノートか確認★★★
        if note_data.get('user_id') != user_id:
            flash('他のユーザーのノートを編集する権限がありません。', 'danger')
            return redirect(url_for('archive_tags'))
            
        note_data['id'] = note_id
        return render_template('edit_note.html', note=note_data)
    else:
        return "エラー: 指定されたノートが見つかりません。", 404

@app.route('/update_note/<note_id>', methods=['POST'])
def update_note(note_id):
    # ▼▼▼【修正点4】セキュリティチェックを追加▼▼▼
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))

    note_ref = db.collection('notes').document(note_id)
    # ★★★更新前に、本当に自分のノートか確認★★★
    note_doc = note_ref.get()
    if not note_doc.exists or note_doc.to_dict().get('user_id') != user_id:
        flash('他のユーザーのノートを更新する権限がありません。', 'danger')
        return redirect(url_for('archive_tags'))

    note_ref.update({
        'ocr_text': request.form['ocr_text'],
        'ai_result': request.form['ai_result']
    })
    return redirect(url_for('archive_tags'))

@app.route('/delete_note/<note_id>', methods=['POST'])
def delete_note(note_id):
    # ▼▼▼【修正点4】セキュリティチェックを追加▼▼▼
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))

    note_ref = db.collection('notes').document(note_id)
    # ★★★削除前に、本当に自分のノートか確認★★★
    note_doc = note_ref.get()
    if not note_doc.exists or note_doc.to_dict().get('user_id') != user_id:
        flash('他のユーザーのノートを削除する権限がありません。', 'danger')
        return redirect(url_for('archive_tags'))
    
    note_ref.delete()
    flash('ノートを削除しました。', 'success')
    return redirect(url_for('archive_tags'))

@app.route('/regenerate_quiz/<note_id>', methods=['POST'])
def regenerate_quiz(note_id):
    # ▼▼▼【修正点4】セキュリティチェックを追加▼▼▼
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))

    note_ref = db.collection('notes').document(note_id)
    note_doc = note_ref.get()
    # ★★★再生成前に、本当に自分のノートか確認★★★
    if not note_doc.exists or note_doc.to_dict().get('user_id') != user_id:
        flash('他のユーザーのノートを再生成する権限がありません。', 'danger')
        return redirect(url_for('archive_tags'))

    try:
        note_data = note_doc.to_dict()
        if note_data and 'ocr_text' in note_data:
            new_ai_result = generate_study_content_from_text(note_data['ocr_text'])
            note_ref.update({'ai_result': new_ai_result})
            flash('AIによる再生成が完了しました。', 'success')
    except Exception as e:
        flash(f"再生成中にエラーが発生しました: {e}", 'danger')
        
    return redirect(url_for('archive_tags'))

# ▼▼▼【修正点5】このブロックをファイルの最後に移動▼▼▼
if __name__ == '__main__':
    app.run(debug=True)