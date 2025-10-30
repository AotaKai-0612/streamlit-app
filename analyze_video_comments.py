# -----------------------------------------------------------
# ステップ1：ライブラリの読み込みとAPIキーの設定
# -----------------------------------------------------------
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from openai import OpenAI
import pandas as pd
import json
from tqdm import tqdm
import time

# .envファイルから環境変数を読み込む
load_dotenv()

# YouTube Data APIキー
try:
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY が .env ファイルに見つかりません。")
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    print("✅ YouTube APIキーの読み込みに成功しました。")
except Exception as e:
    print(f"🛑 YouTube APIキーの読み込みエラー: {e}")

# OpenAI APIキー
try:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY が .env ファイルに見つかりません。")
    client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ OpenAI APIキーの読み込みに成功しました。")
except Exception as e:
    print(f"🛑 OpenAI APIキーの読み込みエラー: {e}")

# -----------------------------------------------------------
# ステップ3：YouTubeコメント取得関数
# -----------------------------------------------------------
def get_youtube_comments(video_id, max_comments=200):
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            textFormat="plainText",
            order="relevance"  # ★人気順で取得
        )

        while request and len(comments) < max_comments:
            response = request.execute()
            for item in response["items"]:
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment)
            request = youtube.commentThreads().list_next(request, response)

        print(f"✅ {len(comments)}件のコメントを取得しました。")
        return comments[:max_comments]
    except Exception as e:
        print(f"🛑 コメント取得エラー: {e}")
        return []

# -----------------------------------------------------------
# ステップ4：GPTによるコメント分析関数（★Colabの定義をそのまま使用）
# -----------------------------------------------------------
def analyze_comment(comment_text):
    prompt = f"""
    あなたはYouTubeコメントを分析する専門家です。
    以下のルールに【厳密に】従って、指定されたYouTubeコメントを6つの特徴量で分析し、JSON形式で出力してください。
    コメントの表面上の意味だけでなく、文脈的・反語的な意味（例：「良い動画なのでいいねを二回押しました！」などの皮肉表現）も考慮して評価してください。

    # 分析ルール

    ##  1. 攻撃性 (Aggressiveness)
    - **何を測るか**: コメントに含まれる、他者への直接的な敵意、侮辱、脅迫の度合い。
    - **レベル0: なし**: 敬意が払われている、もしくは中立的。無礼な言葉遣いが一切含まれない。（例: 「いつも動画ありがとうございます。」）
    - **レベル1: 低**: 相手を小馬鹿にする、見下すような表現。直接的な暴言ではないが、無礼で相手を不快にさせる可能性がある。（例: 「そんなことも知らないの？」）
    - **レベル2: 中**: 特定の個人や意見に対する直接的な悪口、人格否定、嘲笑。「バカ」「キモい」など、明確な敵意や侮辱が含まれる。（例: 「こいつマジで頭悪いな。」）
    - **レベル3: 高**: 脅迫、ヘイトスピーチ、自殺の教唆など、心身の安全を脅かす表現。（例: 「こういう奴は社会から消えろ。」）

    ##  2. 挑発性 (Provocation)
    - **何を測るか**: 皮肉、嫌味、決めつけ、煽りなど、相手の感情を逆撫でして反応を引き出そうとする意図の度合い。
    - **レベル0: なし**: 誠実でストレートな表現。裏の意図を感じさせない。（例: 「編集お疲れ様です！」）
    - **レベル1: 低**: 軽度の皮肉や嫌味。分かる人には分かるが、文字通り受け取ることもできるような、曖昧さを含む表現。（例: 「謝罪動画でがっぽり稼げてよかったね。」）
    - **レベル2: 中**: 明確な「上から目線」、レッテル貼り、意図的な揚げ足取り。「信者」「アンチ」などの言葉を使い、対立を煽る。（例: 「信者さんたちが必死に擁護してて草。」）
    - **レベル3: 高**: 議論を破壊し、場を荒らすことを目的とした悪質な煽り。（例: 「はい論破。反論できないなら俺の勝ちね。」）

    ##  3. 有用性 (Usefulness)
    - **何を測るか**: 動画の内容や他の視聴者に対して、有益な価値を提供している度合い。
    - **レベル0: なし**: 「草」「好き」など、中身のない相槌や単なる感情表現。（例: 「草」）
    - **レベル1: 低**: 具体的な根拠のない、個人の感想や漠然とした意見。（例: 「今回の動画面白くなかったな。」）
    - **レベル2: 中**: 具体的な指摘、改善提案、根拠のある意見、体験談など、参考になる情報を含む。（例: 「BGMが大きすぎてナレーションが聞き取りづらかったです。」）
    - **レベル3: 高**: 専門的な知識に基づく深い分析、データや出典を用いた客観的な訂正など、極めて価値の高い情報を含む。（例: 「この件、〇〇という法律の第△条に抵触する可能性があります。」）

    ##  4. 感情極性 (Sentiment Polarity)
    - **何を測るか**: コメント全体の感情的なトーン。
    - **レベル-2: 強いネガティブ**: 強い怒り、憎しみ、軽蔑など。（例: 「史上最悪の動画。時間の無駄だった。」）
    - **レベル-1: ネガティブ**: 批判、失望、不満など。（例: 「期待してた内容と違って少し残念でした。」）
    - **レベル0: 中立**: 事実の記述、質問など、感情的な色合いがほとんどない。（例: 「この商品はどこで買えますか？」）
    - **レベル+1: ポジティブ**: 好意、感謝、賞賛など。（例: 「面白かったです！次回の動画も楽しみにしています！」）
    - **レベル+2: 強いポジティブ**: 感動、熱狂、深い感謝など。（例: 「感動で涙が出ました。一生ついていきます！」）

    ##  5. 自己顕示性 (Self-display / Superiority)
    - **何を測るか**: 自分の知識や経験などをアピールし、優位に立とうとする意図の度合い。
    - **レベル0: なし**: 自分をアピールする意図が見られない。（例: 「この考え方は面白いですね。」）
    - **レベル1: 低**: 話題に関連した自分の体験談や知識を、補足情報として共有している。（例: 「私が昔〇〇に行った時も同じような感じでしたよ。」）
    - **レベル2: 中**: 投稿者の説明に対し、訂正や補足という形で、より専門的な知識や自身の成功体験を披露し、暗に優位性を示している。（例: 「インデックス投資は初心者向けですよね。僕はそれで資産8桁いきました。」）
    - **レベル3: 高**: 経歴、年収などを提示し、他者を直接的・間接的に見下す。（例: 「年収〇〇万以下の人はこの動画見ても意味ないよ。」）

    ##  6. 文脈依存性 (Context-dependency / In-groupness)
    - **何を測るか**: 内輪にしか真意が伝わらない、専門用語や内輪ネタがどの程度含まれているか。
    - **レベル0: なし**: 誰が読んでも理解できる、一般的で平易な言葉遣い。（例: 「今日の夕飯はカレーにしようと思います。」）
    - **レベル1: 低**: 過去の動画での出来事に言及しているが、文脈を知らなくても大意は推測できる。（例: 「前回の動画で言ってた〇〇の件、解決してよかった！」）
    - **レベル2: 中**: ファンの間だけで通じる愛称、ミーム、決まり文句などが使われており、初見には意味が分かりにくい。（例: 「さすが〇〇さん（ファンの愛称）、今日も平常運転で安心した。」）
    - **レベル3: 高**: 背景知識がなければ、コメントの意味を全く理解できない。（例: 「今日の動画は完全に『例のあの件』だな…」）
    
    最後に総合コメントとして、なぜそのように評価をしたのか説明をしてください。

    # 出力フォーマット（JSON）
    必ず **有効なJSON形式** で出力してください。
    数値には「+」を付けず、引用符の閉じ忘れやコメントは入れないでください。
    {{
      "攻撃性": {{"score": 0-3 }},
      "挑発性": {{"score": 0-3 }},
      "有用性": {{"score": 0-3 }},
      "感情極性": {{"score": -2〜+2 }},
      "自己顕示性": {{"score": 0-3 }},
      "文脈依存性": {{"score": 0-3 }},
      "総合コメント": "..."
    }}

    # 分析対象コメント
    {comment_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        raw_output = response.choices[0].message.content.strip()

        try:
            result = json.loads(raw_output)
        except json.JSONDecodeError:
            result = {"raw_output": raw_output}
        return result

    except Exception as e:
        return {"error": str(e)}

# -----------------------------------------------------------
# ステップ5：全コメントを一括分析してCSV保存
# -----------------------------------------------------------
def analyze_video_comments(video_url, max_comments=200, save_path="analyzed_comments.csv"):
    # URLから動画IDを抽出
    video_id = None
    if "v=" in video_url:
        video_id = video_url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in video_url:
         video_id = video_url.split("youtu.be/")[-1].split("?")[0]
    
    if not video_id:
        print("⚠️ 無効なYouTube URLです。")
        return

    comments = get_youtube_comments(video_id, max_comments)
    if not comments:
        print("コメントが取得できなかったため、処理を終了します。")
        return

    results = []

    for c in tqdm(comments, desc="Analyzing comments"):
        analysis = analyze_comment(c)
        time.sleep(0.5)  # API制限対策

        record = {"コメント": c}
        record.update({k: v.get("score", None) if isinstance(v, dict) else v for k, v in analysis.items()})
        results.append(record)

    df = pd.DataFrame(results)
    df.to_csv(save_path, index=False)
    print(f"✅ 分析結果を {save_path} に保存しました。")
    return df

# -----------------------------------------------------------
# ステップ6：実行（このファイルが直接実行された時だけ動く）
# -----------------------------------------------------------
if __name__ == "__main__":
    print("YouTubeコメント一括分析スクリプト")
    video_url = input("🎥 分析したいYouTube動画のURLを入力してください：")
    if video_url:
        df = analyze_video_comments(video_url, max_comments=50) # テスト用に50件に設定
        if df is not None:
            print(df.head())