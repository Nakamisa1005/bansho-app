import pytesseract
from PIL import Image
import google.generativeai as genai
import os

# --- Tesseract OCRのパス設定（Windowsで必要な場合） ---
# ご自身の環境に合わせてパスを修正してください
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- Gemini APIキーの設定 ---

genai.configure(api_key="AIzaSyD-NwU9b-24GGDhguZpNYWsDEg7Pz8bGys")

# ==============================================================================
# 関数1: 画像から文字を認識する (OCR機能)
# ==============================================================================
def perform_ocr(image_path):
    """
    指定された画像ファイルから文字認識を行います。
    """
    if not os.path.exists(image_path):
        print(f"エラー: 画像ファイルが見つかりません - {image_path}")
        return None
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='jpn+eng')
        return text
    except Exception as e:
        print(f"OCR処理中にエラーが発生しました: {e}")
        return None

# ==============================================================================
# 関数2: テキストから学習コンテンツを生成する (AI機能)
# ==============================================================================
def generate_study_content_from_text(text):
    """
    入力されたテキストから、AIを使って学習コンテンツを生成します。
    """
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

# ==============================================================================
# メイン処理: 2つの関数を連携させる
# ==============================================================================
if __name__ == "__main__":
    # --- 処理したい画像ファイルのパスを指定 ---
    # 手書きのノートを撮影した画像や、教科書の写真などに変更して試してください
    input_image_path = 'images/admission.png' 

    print(f"処理を開始します: {input_image_path}\n")

    # Step 1: 画像からテキストを抽出
    print("--- 1. OCRによるテキスト抽出を実行中... ---")
    extracted_text = perform_ocr(input_image_path)

    if not extracted_text or extracted_text.strip() == "":
        print("\nテキストが抽出できませんでした。処理を終了します。")
    else:
        print("--- テキスト抽出完了 ---")
        print("▼抽出されたテキスト:")
        print(extracted_text)
        print("------------------------\n")

        # Step 2: 抽出したテキストから学習コンテンツを生成
        print("--- 2. AIによる学習コンテンツ生成を実行中... ---")
        study_content = generate_study_content_from_text(extracted_text)

        print("--- AIによる生成完了 ---")
        print("▼生成された学習コンテンツ:")
        print(study_content)
        print("------------------------\n")
        
        print("全ての処理が完了しました。")