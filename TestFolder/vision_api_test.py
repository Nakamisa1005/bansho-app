import os
from google.cloud import vision

# --- 準備：認証情報（鍵ファイル）の設定 ---
# ステップ1でダウンロードしたJSONファイルのパスを、ここに設定してください。
# Windowsの場合の例: r"C:\Users\Naito\Downloads\my-project-credentials.json"
# Macの場合の例: "/Users/Naito/Downloads/my-project-credentials.json"
# このスクリプトと同じフォルダに鍵ファイルを置くと、ファイル名だけで指定できます。
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'bansho-ocr-app-a38c8bdf8a75.json'


def detect_text_with_vision_api(image_path):
    """
    Google Cloud Vision APIを使って、画像から高精度に文字を検出する関数
    """
    # Vision APIのクライアント（操作の窓口）を作成
    client = vision.ImageAnnotatorClient()

    # 画像ファイルをバイナリデータとして読み込む
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    # Vision APIが扱える形式に画像を変換
    image = vision.Image(content=content)

    # Vision APIの「ドキュメントテキスト検出」機能を呼び出す
    # 手書き文字や、文章構造の認識に強いモードです。
    response = client.document_text_detection(image=image)
    
    # エラーが発生した場合
    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))

    # 検出されたテキスト全体を返す
    return response.full_text_annotation.text


if __name__ == "__main__":
    # 認識させたい手書き画像のパスを指定
    image_file_path = 'images/test_handwriting.jpg'

    print(f"--- ☁️ Google Cloud Vision APIによる文字認識を実行します ---")
    print(f"対象ファイル: {image_file_path}")

    try:
        # Vision APIを呼び出してテキストを抽出
        detected_text = detect_text_with_vision_api(image_file_path)
        
        print("\n【✨ 認識結果 ✨】")
        print(detected_text)

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")