import os
from flask import Flask, render_template, request
import cv2
import pytesseract
import google.generativeai as genai

app = Flask(__name__)

#画像を一時的に保存するフォルダのパス設定
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Gemini APIキーの設定 ---
genai.configure(api_key="AIzaSyD-NwU9b-24GGDhguZpNYWsDEg7Pz8bGys")

#openCVの処理
def preprocess_image_for_ocr(image_path):
    """
    OpenCVを使い、OCRの精度を向上させるための画像前処理を行います。
    """
    # 1. 画像を読み込む
    img = cv2.imread(image_path)
    if img is None:
        print(f"エラー: 画像が読み込めませんでした - {image_path}")
        return None

    # 2. グレースケール化：色情報をなくし、白黒の濃淡にします。
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3. 二値化：画像を完全な白と黒の2色に分けます。これにより文字と背景が明確になります。
    #    cv2.THRESH_OTSUは、最適な閾値を自動で設定してくれる賢い方法です。
    _, binary_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 4. ノイズ除去：小さな点やかすれを除去します。
    #    メディアンフィルタは、特にゴマ塩ノイズに効果的です。
    denoised_img = cv2.medianBlur(binary_img, 3)

    # 処理後の画像を返す
    return denoised_img

#OCR機能
def perform_ocr(processed_image): # 処理済みの画像データを受け取る
    """
    前処理された画像データから文字認識を行います。
    """
    try:
        # Pytesseractに処理済みの画像データを直接渡す
        text = pytesseract.image_to_string(processed_image, lang='jpn+eng')
        return text
    except Exception as e:
        print(f"OCR処理中にエラーが発生しました: {e}")
        return None

#AI機能
def generate_study_content_from_text(text):
    """
    入力されたテキストから、AIを使って学習コンテンツを生成します。
    """
    # （この関数の中身は変更ありません）
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    あなたは優秀な学習アシスタントです。
    以下のテキストは、学生がスマートフォンのカメラで撮影したノートや板書の一部です。
    このテキストから、学生が復習しやすいように以下の3つの要素を抽出・生成してください。

    1. **要点まとめ**: テキスト全体の内容を箇条書きで簡潔にまとめてください。
    2. **重要キーワード**: 学習する上で重要だと思われる単語を3〜5個挙げてください。
    3. **復習問題**: 内容を理解できているか確認するための問題を3問（穴埋め、正誤問題など形式は問わない）作成し、答えも併記してください。

    ---
    【元のテキスト】
    {text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI処理中にエラーが発生しました: {e}"


# --- トップページ('/')の処理 ---
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
        # 1. アップロードされたファイルを安全なファイル名にして、一時保存する
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 2. 保存した画像に対して、これまでの処理を順番に実行する
        preprocessed_image = preprocess_image_for_ocr(filepath)
        
        if preprocessed_image is None:
            return "エラー: 画像の前処理に失敗しました。"

        extracted_text = perform_ocr(preprocessed_image)

        if not extracted_text or extracted_text.strip() == "":
             # 抽出したテキストを結果として表示する場合
            return render_template('result.html', result_text="テキストを抽出できませんでした。")

        # 3. 抽出したテキストをAIに渡して、最終結果を生成する
        final_result = generate_study_content_from_text(extracted_text)

        # 4. 生成した結果を新しいHTMLテンプレートに渡して表示する
        #    result_textという名前で、final_resultの内容をHTMLに送ります。
        return render_template('result.html', 
                                extracted_text_data=extracted_text,
                                result_text=final_result)

    return "エラー: 不明なエラーが発生しました。"


if __name__ == '__main__':
    # uploadsフォルダがなければ作成する
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)