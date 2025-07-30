import cv2
import pytesseract
from PIL import Image

# --- Tesseract OCRのパス設定（Windowsで必要な場合） ---
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image_path, enable_binary=True):
    """
    OpenCVを使って画像の前処理を行う
    enable_binary: Trueにすると二値化まで行い、Falseだとグレースケールのみ
    """
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    # 1. グレースケール化
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if enable_binary:
        # 2. 二値化 (Otsu's method)
        # これが「前処理あり」の画像
        _, processed_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        # これが「前処理なし（グレースケールのみ）」の画像
        processed_img = gray

    return processed_img

def perform_ocr(image_data):
    """画像データから文字認識を行う"""
    try:
        text = pytesseract.image_to_string(image_data, lang='jpn+eng')
        return text
    except Exception as e:
        return f"OCR処理中にエラー: {e}"

if __name__ == "__main__":
    # ここに、先ほど作成した手書き画像のパスを指定してください
    image_file = 'images/test_handwriting.jpg'

    # --- 実験1: 前処理「なし」(グレースケールのみ) の場合 ---
    print("--- 🔬 実験1: 前処理「なし」の場合 ---")
    img_no_preprocessing = preprocess_image(image_file, enable_binary=False)
    if img_no_preprocessing is not None:
        text_before = perform_ocr(img_no_preprocessing)
        print("【結果】")
        print(text_before if text_before.strip() else "== テキストを検出できませんでした ==")
    else:
        print("画像を読み込めませんでした。")
    
    print("\n" + "="*40 + "\n")

    # --- 実験2: 前処理「あり」(二値化) の場合 ---
    print("--- 🧪 実験2: 前処理「あり」（二値化）の場合 ---")
    img_with_preprocessing = preprocess_image(image_file, enable_binary=True)
    if img_with_preprocessing is not None:
        text_after = perform_ocr(img_with_preprocessing)
        print("【結果】")
        print(text_after if text_after.strip() else "== テキストを検出できませんでした ==")
    else:
        print("画像を読み込めませんでした。")