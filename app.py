import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re
import concurrent.futures

# ==============
# APIキー読み込み
# ==============
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not YOUTUBE_API_KEY or not OPENAI_API_KEY:
    st.error("❌ APIキーが見つかりません。.env に YOUTUBE_API_KEY と OPENAI_API_KEY を記述してください。")
    st.stop()

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# ==============
# Streamlit設定
# ==============
st.set_page_config(page_title="YouTubeコメント分析システム", layout="wide")
st.title("🎥 YouTubeコメント分析システム（完全版）")

FEATURES = [
    {"key": "攻撃性", "min": 0, "max": 3},
    {"key": "挑発性", "min": 0, "max": 3},
    {"key": "有用性", "min": 0, "max": 3},
    {"key": "感情極性", "min": -2, "max": 2},
    {"key": "自己顕示性", "min": 0, "max": 3},
    {"key": "文脈依存性", "min": 0, "max": 3}
]

# =========================================
# コメント取得（完全動作版）
# =========================================
def get_comments(video_id, max_comments=100):
    comments = []
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText",
        order="relevance"
    )

    while request and len(comments) < max_comments:
        response = request.execute()

        for item in response.get("items", []):
            try:
                txt = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(txt)
            except:
                continue

        if "nextPageToken" not in response:
            break

        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            pageToken=response["nextPageToken"],
            textFormat="plainText",
            order="relevance"
        )

    return comments[:max_comments]

# =========================================
# OpenAI 出力の安全取得
# =========================================
def extract_content(resp):
    """OpenAIレスポンスから確実にテキストを抜き出す"""
    msg = resp.choices[0].message

    # pattern A: content is str
    if isinstance(msg.content, str):
        return msg.content

    # pattern B: content is list of dict
    if isinstance(msg.content, list) and len(msg.content) > 0:
        part = msg.content[0]
        if isinstance(part, dict) and "text" in part:
            return part["text"]

    return ""  # fallback


# =========================================
# GPTコメント分析
# =========================================
def analyze_comment(c):
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
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        raw = extract_content(resp).strip()

        try:
            return json.loads(raw)
        except:
            return {"raw_output": raw}

    except Exception as e:
        return {"error": str(e)}

# =========================================
# 分析結果正規化
# =========================================
def normalize_row(ana):
    row = {}

    for f in FEATURES:
        k = f["key"]
        if isinstance(ana, dict) and k in ana:
            val = ana[k]
            if isinstance(val, dict) and "score" in val:
                row[f"{k}_score"] = val["score"]
            else:
                row[f"{k}_score"] = None
        else:
            row[f"{k}_score"] = None

    row["総合コメント"] = ana.get("総合コメント", ana.get("raw_output", ""))
    return row


# ===================================================
# Session 初期化
# ===================================================
if "selected_video" not in st.session_state:
    st.session_state["selected_video"] = None
if "df" not in st.session_state:
    st.session_state["df"] = None

# ===================================================
# 1. 検索
# ===================================================
if st.session_state["selected_video"] is None:

    query = st.text_input("検索ワードを入力")
    if st.button("検索する"):
        res = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=9
        ).execute()
        st.session_state["results"] = res.get("items", [])

    if "results" in st.session_state:
        for item in st.session_state["results"]:
            vid = item["id"]["videoId"]
            title = item["snippet"]["title"]
            thumb = item["snippet"]["thumbnails"]["medium"]["url"]

            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(thumb)
            with col2:
                st.write(f"**{title}**")
                if st.button("この動画を選択する", key=vid):
                    st.session_state["selected_video"] = vid
                    st.session_state["selected_title"] = title
                    st.experimental_rerun()

# ===================================================
# 2. 動画選択後 → コメント分析
# ===================================================
else:
    vid = st.session_state["selected_video"]
    st.subheader(f"🎞 選択中: {st.session_state['selected_title']}")
    st.video(f"https://www.youtube.com/watch?v={vid}")

    if st.button("🔍 コメント分析（100件）"):
        comments = get_comments(vid)
        st.write(f"取得コメント数: {len(comments)}")

        rows = []
        progress = st.progress(0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            future_map = {ex.submit(analyze_comment, c): c for c in comments}
            for i, future in enumerate(concurrent.futures.as_completed(future_map)):
                c = future_map[future]
                ana = future.result()
                row = normalize_row(ana)
                row["コメント"] = c
                rows.append(row)
                progress.progress((i + 1) / len(comments))

        df = pd.DataFrame(rows)
        st.session_state["df"] = df
        st.success("解析完了！")

    if st.session_state["df"] is not None:
        df = st.session_state["df"]
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 CSVダウンロード",
            data=csv,
            file_name="analysis.csv",
            mime="text/csv"
        )

        if st.button("🔙 動画選択に戻る"):
            st.session_state["selected_video"] = None
            st.session_state["df"] = None
            st.experimental_rerun()



