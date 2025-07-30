import pytesseract
from PIL import Image
import os


def perform_ocr(image_path):
    """
    指定された画像ファイルから文字認識を行います。
    """
    if not os.path.exists(image_path):
        print(f"エラー: 画像ファイルが見つかりません - {image_path}")
        return None

    try:
        # 画像を開く
        img = Image.open(image_path)
        print(f"画像を読み込みました: {image_path}")

        # OCRを実行（日本語と英語を認識）
        # Tesseractのインストール時に日本語言語データにチェックを入れたか確認してください。
        text = pytesseract.image_to_string(img, lang='jpn+eng')
        return text
    except pytesseract.TesseractNotFoundError:
        print("エラー: Tesseract OCRがインストールされていないか、パスが正しく設定されていません。")
        print("Tesseract OCRエンジン本体がインストールされていること、およびPATHが通っていることを確認してください。")
        return None
    except Exception as e:
        print(f"OCR処理中にエラーが発生しました: {e}")
        return None

if __name__ == "__main__":
    # === 画像ファイルのパス ===
    test_image_path = 'images/13wiz.jpg'

    # OCR実行
    recognized_text = perform_ocr(test_image_path)

    if recognized_text:
        print("\n--- 認識されたテキスト ---")
        print(recognized_text)
        print("------------------------")