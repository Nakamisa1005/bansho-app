import os
from flask import Flask, render_template, request, redirect, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import vision
import google.generativeai as genai
import random

# --- Flaskアプリケーションの準備 ---
app = Flask(__name__)

# --- 各種設定 ---
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if __name__ == '__main__':
    # uploadsフォルダがなければ、自動で作成する
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)


firebase_cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
if firebase_cred_path:
    cred = credentials.Certificate(firebase_cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    # ローカルで動かす場合など、環境変数がない場合の fallback
    print("Firebaseの認証情報(環境変数)が見つかりません。")

# Vision APIの認証は、GOOGLE_APPLICATION_CREDENTIALS 環境変数が設定されていれば
# クライアント作成時に自動で読み込まれるため、特別なコードは不要です。

# Gemini APIキーの設定
gemini_api_key = os.environ.get('GEMINI_API_KEY')
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    print("Gemini APIキー(環境変数)が見つかりません。")


# ==============================================================================
# 関数たち（部品）
# ==============================================================================

def detect_text_with_vision_api(image_path):
    """Google Cloud Vision APIを使って、画像から高精度に文字を検出する関数"""
    client = vision.ImageAnnotatorClient()

    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)
    if response.error.message:
        raise Exception(response.error.message)
    return response.full_text_annotation.text

def generate_study_content_from_text(text):
    """テキストから学習コンテンツを生成します。"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    あなたは優秀な学習アシスタントです。
    以下のテキストは、学生が撮影したノートや板書の一部です。
    このテキストから、学生が復習しやすいように以下の3つの要素を抽出・生成してください。

    1. **要点まとめ**: テキスト全体の内容を箇条書きで簡潔にまとめてください。
    2. **重要キーワード**: 重要だと思われる単語を3〜5個挙げてください。
    3. "" 復習問題は、「穴埋め」「選択」「記述」の問題形式をバランス良く織り交ぜてください。
    - 各問題は、以下の厳密な形式に従ってください。

    # 形式
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
# Flaskのルーティング（Webページの各URLの処理）
# ==============================================================================

@app.route('/')
def home():
    """トップページを表示します。"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_and_process():
    """画像のアップロード、処理、結果表示を行います。"""
    if 'image' not in request.files:
        return "エラー: ファイルが選択されていません。"

    file = request.files['image']

    if file.filename == '':
        return "エラー: ファイル名が空です。"

    if file:
        # 0. フォームから送信されたタグを取得
        tag = request.form.get('tag', '未分類') # 入力がない場合は'未分類'とする

        # 1. アップロードされたファイルを一時保存する
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # 保存する直前に、フォルダの存在を確認し、なければ作成する
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file.save(filepath)

        # 2. Vision APIでテキストを抽出する
        try:
            extracted_text = detect_text_with_vision_api(filepath)
        except Exception as e:
            return f"Vision APIでの処理中にエラーが発生しました: {e}"

        if not extracted_text or extracted_text.strip() == "":
            return render_template('result.html',
                                   extracted_text_data="テキストを抽出できませんでした。",
                                   result_text="テキストがないため、AI処理はスキップされました。")

        # 3. 抽出したテキストをAIに渡して、最終結果を生成する
        final_result = generate_study_content_from_text(extracted_text)

        # 4. Firestoreデータベースに結果を保存する
        notes_collection = db.collection('notes')
        notes_collection.add({
            'created_at': firestore.SERVER_TIMESTAMP, # 保存した日時
            'ocr_text': extracted_text,
            'ai_result': final_result,
            'tag': tag
        })
        
        # 5. AIの生成結果から問題部分をパース（解析）する
        quiz_list = []
        quiz_section = final_result.split('復習問題')[-1]
        for line in quiz_section.split('\n'):
            if line.startswith('TYPE:'):
                parts = line.split('@@')
                quiz_type = parts[0].replace('TYPE:', '').strip()
                question_data = {'type': quiz_type}
                if quiz_type == '穴埋め':
                    question_data['question'] = parts[1].replace('QUESTION:', '').strip()
                    question_data['answer'] = parts[2].replace('ANSWER:', '').strip()
                elif quiz_type == '選択':
                    question_data['question'] = parts[1].replace('QUESTION:', '').strip()
                    question_data['choices'] = parts[2].replace('CHOICES:', '').strip().split(',')
                    question_data['answer'] = parts[3].replace('ANSWER:', '').strip()
                elif quiz_type == '記述':
                    question_data['question'] = parts[1].replace('QUESTION:', '').strip()
                    question_data['answer'] = parts[2].replace('ANSWER:', '').strip()
                quiz_list.append(question_data)

        # 6. 最後に、すべての結果をHTMLテンプレートに渡して表示する
        return render_template('result.html',
                               extracted_text_data=extracted_text,
                               result_text=final_result,
                               quizzes=quiz_list) # quiz_listも渡す

    return "エラー: 不明なエラーが発生しました。"

    

# アーカイブページ用の新しいルート
@app.route('/archive')
def archive_tags():
    """保存されているノートのタグ（科目名）を一覧で表示する"""
    notes_ref = db.collection('notes').stream()
    
    # すべてのノートからタグだけを重複なく抽出する
    tags = set()
    for note in notes_ref:
        note_data = note.to_dict()
        if 'tag' in note_data:
            tags.add(note_data['tag'])
            
    return render_template('archive_tags.html', tags=sorted(list(tags)))

@app.route('/archive/<tag_name>')
def archive_by_tag(tag_name):
    """指定されたタグのノートだけを一覧で表示する"""
    notes_ref = db.collection('notes').where('tag', '==', tag_name).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    
    notes_list = []
    for note in notes_ref:
        note_data = note.to_dict()
        note_data['id'] = note.id
        notes_list.append(note_data)
        
    return render_template('archive.html', notes=notes_list, tag_name=tag_name)


# 編集ページを表示するためのルート
@app.route('/note/<note_id>')
def edit_note(note_id):
    """IDを指定して、特定のノートを編集ページに表示する"""
    note_ref = db.collection('notes').document(note_id).get()
    if note_ref.exists:
        note_data = note_ref.to_dict()
        note_data['id'] = note_id
        return render_template('edit_note.html', note=note_data)
    else:
        return "エラー: 指定されたノートが見つかりません。", 404


# 編集内容をDBに保存（更新）するためのルート
@app.route('/update_note/<note_id>', methods=['POST'])
def update_note(note_id):
    """編集された内容で、Firestoreのデータを更新する"""
    note_ref = db.collection('notes').document(note_id)
    
    # フォームから送信されたテキストを取得
    updated_ocr_text = request.form['ocr_text']
    updated_ai_result = request.form['ai_result']
    
    # データベースの値を更新
    note_ref.update({
        'ocr_text': updated_ocr_text,
        'ai_result': updated_ai_result
    })
    
    # 更新後はアーカイブ一覧ページに戻る
     return redirect(url_for('archive_tags'))

# ノートを削除するためのルート
@app.route('/delete_note/<note_id>', methods=['POST'])
def delete_note(note_id):
    """IDを指定して、特定のノートをFirestoreから削除する"""
    try:
        db.collection('notes').document(note_id).delete()
        # 削除後はアーカイブ一覧ページに戻る
        return redirect(url_for('archive'))
    except Exception as e:
        return f"削除中にエラーが発生しました: {e}", 500

# ノートの復習問題を再生成するためのルート
@app.route('/regenerate_quiz/<note_id>', methods=['POST'])
def regenerate_quiz(note_id):
    """指定されたノートのOCRテキストを元に、AIの結果を再生成して更新する"""
    try:
        # 1. IDを元に、Firestoreから該当のノートデータを取得する
        note_ref = db.collection('notes').document(note_id)
        note_data = note_ref.get().to_dict()

        if note_data and 'ocr_text' in note_data:
            ocr_text = note_data['ocr_text']
            
            # 2. 取得したOCRテキストを使って、再度Gemini APIを呼び出す
            new_ai_result = generate_study_content_from_text(ocr_text)
            
            # 3. Firestoreのai_resultフィールドを、新しい生成結果で更新する
            note_ref.update({
                'ai_result': new_ai_result
            })
            
        # 4. 処理が終わったら、アーカイブ一覧ページに戻る
        return redirect(url_for('archive_tags')) # タグ一覧ページにリダイレクト

    except Exception as e:
        return f"再生成中にエラーが発生しました: {e}", 500



if __name__ == '__main__':
    # こちらは開発用のサーバー起動のみ
    app.run(debug=True)