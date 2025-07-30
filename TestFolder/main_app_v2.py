import pytesseract
from PIL import Image
import google.generativeai as genai
import os
import cv2 # OpenCVライブラリをインポート

# --- Tesseract OCRのパス設定（Windowsで必要な場合） ---
# ご自身の環境に合わせてパスを修正してください
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- Gemini APIキーの設定 ---
# ご自身のAPIキーを設定してください
genai.configure(api_key="AIzaSyD-NwU9b-24GGDhguZpNYWsDEg7Pz8bGys")

# ==============================================================================
# ★★新機能★★ 関数: OCRのための画像前処理
# ==============================================================================
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

# ==============================================================================
# 関数: 画像から文字を認識する (OCR機能)
# ==============================================================================
def perform_ocr(processed_image): # ★★変更点: ファイルパスではなく、処理済みの画像データを受け取る★★
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

# ==============================================================================
# 関数: テキストから学習コンテンツを生成する (AI機能)
# ==============================================================================
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

# ==============================================================================
# メイン処理
# ==============================================================================
if __name__ == "__main__":
    input_image_path = 'images/admission.png' # 認識させたい画像を指定

    print(f"処理を開始します: {input_image_path}\n")

    # Step 1: ★★画像の前処理★★
    print("--- 1. OpenCVによる画像の前処理を実行中... ---")
    preprocessed_image = preprocess_image_for_ocr(input_image_path)

    if preprocessed_image is None:
        print("画像の前処理に失敗しました。処理を終了します。")
    else:
        # Step 2: 前処理済みの画像からテキストを抽出
        print("--- 2. OCRによるテキスト抽出を実行中... ---")
        extracted_text = perform_ocr(preprocessed_image) # ★★変更点★★

        if not extracted_text or extracted_text.strip() == "":
            print("\nテキストが抽出できませんでした。処理を終了します。")
        else:
            print("--- テキスト抽出完了 ---")
            print("▼抽出されたテキスト:")
            print(extracted_text)
            print("------------------------\n")

            # Step 3: 抽出したテキストから学習コンテンツを生成
            print("--- 3. AIによる学習コンテンツ生成を実行中... ---")
            study_content = generate_study_content_from_text(extracted_text)

            print("--- AIによる生成完了 ---")
            print("▼生成された学習コンテンツ:")
            print(study_content)
            print("------------------------\n")
            
            print("全ての処理が完了しました。")