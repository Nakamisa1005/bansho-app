import google.generativeai as genai
import os

# --- 準備 ---
# 1. 上記で取得したAPIキーを設定します。
#    直接コードに書くか、環境変数として設定してください。
#    os.environ['GOOGLE_API_KEY'] = "YOUR_API_KEY" # 環境変数を使う場合
genai.configure(api_key="AIzaSyD-NwU9b-24GGDhguZpNYWsDEg7Pz8bGys")

# --- AIモデルの準備 ---
# 使用するAIモデルを指定します。
model = genai.GenerativeModel('gemini-1.5-flash') # 高速でバランスの取れたモデル

def generate_study_content_from_text(text):
    """
    入力されたテキストから、AIを使って学習コンテンツ（要約・キーワード・問題）を生成します。
    """
    # AIへの指示（プロンプト）。この内容を工夫することが研究の鍵になります。
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
        # AIに処理を依頼
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI処理中にエラーが発生しました: {e}"

if __name__ == "__main__":
    # TesseractでOCRしたと仮定したテキストデータ
    # まずはこの固定テキストで試してみましょう。
    ocr_result_text = """
    日本の歴史：戦国時代

    15世紀後半から16世紀後半にかけての約100年間。
    室町幕府の力が弱まり、各地の守護大名が互いに争った。
    代表的な人物：
    ・織田信長：天下統一を目前にするも、本能寺の変で明智光秀に討たれる。「天下布武」を掲げた。
    ・豊臣秀吉：信長の後を継ぎ、天下を統一。太閤検地や刀狩りを実施。
    ・徳川家康：関ヶ原の戦いで勝利し、江戸幕府を開く。260年以上続く江戸時代の基礎を築いた。

    この時代の特徴は「下剋上」。身分の低い者が実力で上の者を倒す風潮があった。
    """

    print("--- 元のテキスト ---")
    print(ocr_result_text)

    # AIによるコンテンツ生成を実行
    print("\n--- AIによる生成結果 ---")
    generated_content = generate_study_content_from_text(ocr_result_text)
    print(generated_content)