import firebase_admin
from firebase_admin import credentials, firestore

# --- 準備：認証情報（鍵ファイル）の設定 ---
# 先ほどダウンロードしたJSONファイルのパスを指定します
cred = credentials.Certificate("C:/Users/sho0l/bansho/bansho-app-firebase-adminsdk-fbsvc-55e1012ff0.json")
firebase_admin.initialize_app(cred)

# Firestoreデータベースへの接続を取得
db = firestore.client()

# --- データの追加テスト ---
# 'notes'というコレクション（データのグループ）に新しいデータを追加
# .add() を使うと、IDは自動で生成されます
doc_ref, doc_id = db.collection('notes').add({
    'ocr_text': 'これはFirebaseのテストです。',
    'ai_result': 'テストに成功しました。',
    'user_id': 'naito_san' # 将来的にユーザーを区別するために使えます
})

print(f"テストデータが正常に追加されました。")
print(f"ドキュメントID: {doc_id.id}")

# --- データの読み取りテスト ---
print("\n--- Firestoreからデータを読み取ります ---")
notes_ref = db.collection('notes')
docs = notes_ref.stream()

for doc in docs:
    print(f'{doc.id} => {doc.to_dict()}')