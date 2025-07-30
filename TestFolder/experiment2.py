import cv2
import pytesseract
from PIL import Image

# --- Tesseract OCRのパス設定（Windowsで必要な場合） ---
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image_path, step=1):
    """
    OpenCVを使って画像の前処理を行う
    step 1: グレースケールのみ
    step 2: 二値化を追加
    step 3: ノイズ除去を追加
    """
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    # 常にグレースケール化は行う
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if step == 1:
        return gray

    # 二値化
    _, binary_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if step == 2:
        return binary_img

    # ノイズ除去
    denoised_img = cv2.medianBlur(binary_img, 3) # 3x3の範囲でノイズ除去
    if step == 3:
        return denoised_img
    
    return None

def perform_ocr(image_data):
    """画像データから文字認識を行う"""
    try:
        text = pytesseract.image_to_string(image_data, lang='jpn+eng')
        return text
    except Exception as e:
        return f"OCR処理中にエラー: {e}"

if __name__ == "__main__":
    image_file = 'images/test_handwriting.jpg' # 前回と同じ手書き画像を使用

    # --- 実験1: 前処理「なし」 ---
    print("--- 🔬 実験1: 前処理「なし」の場合 ---")
    img1 = preprocess_image(image_file, step=1)
    if img1 is not None:
        text1 = perform_ocr(img1)
        print("【結果】\n" + (text1 if text1.strip() else "== テキストを検出できませんでした =="))
    else:
        print("画像を読み込めませんでした。")
    
    print("\n" + "="*40 + "\n")

    # --- 実験2: 「二値化」を追加 ---
    print("--- 🧪 実験2: 「二値化」を追加した場合 ---")
    img2 = preprocess_image(image_file, step=2)
    if img2 is not None:
        text2 = perform_ocr(img2)
        print("【結果】\n" + (text2 if text2.strip() else "== テキストを検出できませんでした =="))
    else:
        print("画像を読み込めませんでした。")

    print("\n" + "="*40 + "\n")

    # --- 実験3: 「ノイズ除去」を追加 ---
    print("--- ✨ 実験3: 「ノイズ除去」を追加した場合 ---")
    img3 = preprocess_image(image_file, step=3)
    if img3 is not None:
        text3 = perform_ocr(img3)
        print("【結果】\n" + (text3 if text3.strip() else "== テキストを検出できませんでした =="))
    else:
        print("画像を読み込めませんでした。")