import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import vision
import google.generativeai as genai
import pyrebase
from dotenv import load_dotenv
from google.api_core import exceptions

load_dotenv()

# Flaskアプリケーションの準備
app = Flask(__name__)
app.secret_key = 'a-very-secret-and-random-key' 

# 各種設定
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Firebase 
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
auth = firebase.auth()

# Firebase Admin SDK (Firestore)
firebase_cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
if firebase_cred_path:
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print("Firebaseの認証情報(環境変数)が見つかりません。")

# Gemini APIキーの設定 Renderに書いてある
gemini_api_key = os.environ.get('GEMINI_API_KEY')
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    print("Gemini APIキー(環境変数)が見つかりません。")

# ==============================================================================
# 関数
# ==============================================================================
# OCR
def detect_text_with_vision_api(image_path):
    client = vision.ImageAnnotatorClient()
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    if response.error.message:
        raise Exception(response.error.message)
    return response.full_text_annotation.text

# AI生成 geminiのmodel
def generate_study_content_from_text(text):
    model_candidates = [
        'gemini-2.0-flash',  
        'gemini-2.0-flash-lite',    
        'gemini-2.5-flash',      
        'gemini-flash-latest',    
        'gemini-2.0-flash-lite-preview-02-05' 
    ]

    prompt = f"""
    あなたは「優秀な参考書の執筆者」です。
    以下の【元のテキスト】（学生のノート）をもとに、自然な解説文を作成してください。

    ---
    ### 役割1：要約パート（自然な文章）
    **「だ・である」調**で、教科書の本文のような自然な文章で書いてください。
    
    【重要な禁止事項】
    - **太字（**文字**）などのMarkdown装飾は一切使用しないでください。**
    - 箇条書き（- ）を多用せず、普通の段落で文章を繋げてください。
    - 「以下にまとめます」のような前置きは不要です。いきなり解説から始めてください。

    1. **要点まとめ**: 
       - ノートの内容を整理し、一つの読み物として成立する文章にする。
       - 機械的な羅列ではなく、接続詞（しかし、また、そのため）を使って滑らかに繋げる。
    
    2. **重要キーワード**: 
       - 重要語句を単に並べてください（装飾不要）。

    ---
    ### 役割2：問題データ生成パート（厳格なフォーマット）
    **ここからはプログラム処理用です。指定されたフォーマットを一字一句守ってください。**
    - Markdown装飾、挨拶、説明は一切不要です。
    - 区切り文字「@@」を改行しないでください。

    3. **復習問題**: 
       - 以下の形式のみを出力してください。

    # 厳守するフォーマット
    TYPE:穴埋め@@QUESTION:（問題文。空欄は〇〇とする）@@ANSWER:（答え）
    TYPE:選択@@QUESTION:（問題文）@@CHOICES:（選択肢1）,（選択肢2）,（選択肢3）@@ANSWER:（答え）
    TYPE:記述@@QUESTION:（問題文）@@ANSWER:（模範解答の要点）

    ---
    【元のテキスト】
    {text}
    ---
    """
    # model_candidatesの中から一つずつ試していく
    for model_name in model_candidates:
        try:
            print(f"🔄 モデル {model_name} で生成を試みています...")
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content(prompt)
            
            # 成功したらテキストを返して終了
            print(f"成功！ ({model_name} を使用)")
            return response.text.replace('•', '  *')

        except exceptions.ResourceExhausted:
            print(f"モデル {model_name} は混雑しています。次を試します。")
            continue
        except Exception as e:
            print(f"エラー ({model_name}): {e}")
            continue
    
    return """
    APIが混み合っているため、処理に失敗しました。しばらく待ってから再度お試しください。
    """

# 復習問題
def parse_quiz_text(text):
    """AIが生成したテキストから、復習問題の部分だけを抜き出してリスト化する"""
    quizzes = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('TYPE:'):
            try:
                quiz = {}
                parts = line.split('@@')
                
                for part in parts:
                    if part.startswith('TYPE:'):
                        quiz['type'] = part.replace('TYPE:', '').strip()
                    elif part.startswith('QUESTION:'):
                        quiz['question'] = part.replace('QUESTION:', '').strip()
                    elif part.startswith('ANSWER:'):
                        quiz['answer'] = part.replace('ANSWER:', '').strip()
                    elif part.startswith('CHOICES:'):
                        choices_str = part.replace('CHOICES:', '').strip()
                        quiz['choices'] = [c.strip() for c in choices_str.split(',')]
                
                if 'type' in quiz and 'question' in quiz:
                    quizzes.append(quiz)
            
            except Exception as e:
                print(f"パースエラー: {line}, {e}")
                continue
    return quizzes

# ==============================================================================
# ログイン・登録
# ==============================================================================
#新規登録
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

#ログイン
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

# ==============================================================================
# Webページの処理
# ==============================================================================
#ホーム画面
@app.route('/')
def home():
    if 'user' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

#アップロード
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
            # 1. OCR
            extracted_text = detect_text_with_vision_api(filepath)
            
            # 2. AI生成
            final_result = generate_study_content_from_text(extracted_text)
            
            # 3. DB保存
            db.collection('notes').add({
                'user_id': user_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'ocr_text': extracted_text,
                'ai_result': final_result,
                'tag': tag
            })
            
            # 4. クイズのパース
            quizzes_data = parse_quiz_text(final_result)
            
            #5. 要約部分だけを綺麗に切り取る処理
            if "TYPE:" in final_result:
                summary_text = final_result.split("TYPE:")[0]
                summary_text = summary_text.replace("3. **復習問題**:", "").replace("3. 復習問題:", "").strip()
            else:
                summary_text = final_result

            return render_template(
                'result.html', 
                extracted_text_data=extracted_text, 
                summary_text=summary_text,
                quizzes=quizzes_data
            )
            
        except Exception as e:
            return f"処理中にエラーが発生しました: {e}"
    return "エラー: 不明なエラーが発生しました。"

# AIによる記述問題の簡易採点用API
@app.route('/check_descriptive', methods=['POST'])
def check_descriptive():
    data = request.get_json()
    user_answer = data.get('user_answer')
    model_answer = data.get('model_answer')
    
    model = genai.GenerativeModel('gemini-2.0-flash-lite')
    prompt = f"""
    あなたは採点官です。
    以下の「模範解答」と「ユーザーの回答」を比較し、意味が合っていれば「正解」、間違っていれば「不正解」とだけ答えてください。
    
    模範解答: {model_answer}
    ユーザーの回答: {user_answer}
    """
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        # 「正解」という言葉が含まれていれば正解とする
        if "正解" in result and "不正解" not in result:
            return jsonify({'result': '正解'})
        else:
            return jsonify({'result': '不正解'})
    except Exception:
        return jsonify({'result': '判定不能'})

#アーカイブ
@app.route('/archive')
def archive_tags():
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))

    notes_ref = db.collection('notes').where('user_id', '==', user_id).stream()
    tags = set()
    for note in notes_ref:
        note_data = note.to_dict()
        if 'tag' in note_data:
            tags.add(note_data['tag'])
    return render_template('archive_tags.html', tags=sorted(list(tags)))

#タグ別アーカイブ
@app.route('/archive/<tag_name>')
def archive_by_tag(tag_name):
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

#ノート編集
@app.route('/note/<note_id>')
def edit_note(note_id):
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))
        
    note_ref = db.collection('notes').document(note_id).get()
    if note_ref.exists:
        note_data = note_ref.to_dict()
        if note_data.get('user_id') != user_id:
            flash('他のユーザーのノートを編集する権限がありません。', 'danger')
            return redirect(url_for('archive_tags'))
            
        note_data['id'] = note_id
        return render_template('edit_note.html', note=note_data)
    else:
        return "エラー: 指定されたノートが見つかりません。", 404

#ノート更新
@app.route('/update_note/<note_id>', methods=['POST'])
def update_note(note_id):
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))

    note_ref = db.collection('notes').document(note_id)
    note_doc = note_ref.get()
    if not note_doc.exists or note_doc.to_dict().get('user_id') != user_id:
        flash('他のユーザーのノートを更新する権限がありません。', 'danger')
        return redirect(url_for('archive_tags'))

    note_ref.update({
        'ocr_text': request.form['ocr_text'],
        'ai_result': request.form['ai_result']
    })
    return redirect(url_for('archive_tags'))

#ノート削除
@app.route('/delete_note/<note_id>', methods=['POST'])
def delete_note(note_id):
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))

    note_ref = db.collection('notes').document(note_id)
    note_doc = note_ref.get()
    if not note_doc.exists or note_doc.to_dict().get('user_id') != user_id:
        flash('他のユーザーのノートを削除する権限がありません。', 'danger')
        return redirect(url_for('archive_tags'))
    
    note_ref.delete()
    flash('ノートを削除しました。', 'success')
    return redirect(url_for('archive_tags'))

#復習問題再生成
@app.route('/regenerate_quiz/<note_id>', methods=['POST'])
def regenerate_quiz(note_id):
    if 'user' not in session: return redirect(url_for('login'))
    try:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
    except Exception:
        return redirect(url_for('logout'))

    note_ref = db.collection('notes').document(note_id)
    note_doc = note_ref.get()
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

if __name__ == '__main__':
    app.run(debug=True)

#ログアウト
@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))