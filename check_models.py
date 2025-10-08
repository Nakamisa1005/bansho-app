import google.generativeai as genai
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを設定
gemini_api_key = os.environ.get('GEMINI_API_KEY')
if not gemini_api_key:
    print("Gemini APIキーが設定されていません。")
else:
    genai.configure(api_key=gemini_api_key)

    print("利用可能なモデル一覧:")
    print("--------------------")
    try:
        for m in genai.list_models():
            # generateContent（テキスト生成）が使えるモデルのみを表示
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"モデルの取得中にエラーが発生しました: {e}")