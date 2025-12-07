import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from openai import OpenAI
from dotenv import load_dotenv
import os
import time
import json
import re
import concurrent.futures

# 1. 環境設定 ---------------------------------------------------------
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not YOUTUBE_API_KEY or not OPENAI_API_KEY:
    st.error("❌ APIキーが見つかりません。.env に YOUTUBE_API_KEY と OPENAI_API_KEY を設定してください。")
    st.stop()

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="YouTubeコメント分析システム", layout="wide")
st.title("🎥 YouTubeコメント分析システム")
st.markdown("キーワード検索 → 動画選択 → コメント取得 → GPTで自動分析（gpt-4o-mini）")

# 2. 定数・ヘルパー関数（旧コードベース） ----------------------------------
FEATURES = [
    {"key": "攻撃性", "min": 0, "max": 3, "desc": "他者への直接的な敵意・侮辱・脅迫の度合い。0=なし, 3=高"},
    {"key": "挑発性", "min": 0, "max": 3, "desc": "皮肉・煽り等で反応を引き出す度合い。0=なし, 3=高"},
    {"key": "有用性", "min": 0, "max": 3, "desc": "動画や視聴者にとって有益か（0=なし, 3=高）"},
    {"key": "感情極性", "min": -2, "max": 2, "desc": "感情のトーン。-2=強いネガティブ, 0=中立, +2=強いポジティブ"},
    {"key": "自己顕示性", "min": 0, "max": 3, "desc": "自分の知識や経歴で優位性を示す度合い"},
    {"key": "文脈依存性", "min": 0, "max": 3, "desc": "内輪ネタや専門用語の頻度。0=わかりやすい, 3=高度に依存"}
]

def extract_number_from_text(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return s
    m = re.search(r"-?\d+(\.\d+)?", str(s))
    if m:
        try:
            if '.' in m.group(0):
                return float(m.group(0))
            else:
                return int(m.group(0))
        except:
            return None
    return None

def normalize_analysis_to_row(analysis):
    row = {}
    reasons = []
    model_overall = None
    if isinstance(analysis, dict):
        model_overall = analysis.get("総合コメント") or analysis.get("総合評価") or analysis.get("総合") or analysis.get("総合コメント（要約）")
    for f in FEATURES:
        k = f["key"]
        val = None
        score = None
        reason = None
        if isinstance(analysis, dict):
            val = analysis.get(k)
        if isinstance(val, dict):
            score = val.get("score") if "score" in val else extract_number_from_text(val.get("value") or val.get("level") or None)
            reason = val.get("reason") or val.get("explanation") or None
        elif isinstance(val, (int, float)):
            score = val
        elif isinstance(val, str):
            score = extract_number_from_text(val)
            reason = re.sub(r"-?\d+(\.\d+)?", "", val).strip(" :,-。．")
            if reason == "":
                reason = None
        if score is None and isinstance(analysis, dict):
            alt_key = f"{k}_score"
            if alt_key in analysis:
                score = extract_number_from_text(analysis.get(alt_key))
            alt2 = k.lower() + "_score"
            if score is None and alt2 in analysis:
                score = extract_number_from_text(analysis.get(alt2))
        row[f"{k}_score"] = score
        if reason:
            reasons.append(f"{k}：{reason}")
    if model_overall and isinstance(model_overall, str) and model_overall.strip():
        overall = model_overall
    else:
        if reasons:
            overall = "モデル理由に基づく総合コメント — " + "；".join(reasons[:6])
        else:
            if isinstance(analysis, dict) and "raw_output" in analysis:
                overall = f"モデル出力（非JSON）: {str(analysis['raw_output'])[:300]}"
            elif isinstance(analysis, dict) and any(k not in [f"{ft['key']}_score" for ft in FEATURES] for k in analysis.keys()):
                overall = "モデル出力: " + ", ".join(list(analysis.keys())[:5])
            else:
                overall = "自動生成された総合コメント：詳細な理由がモデルから得られませんでした。"
    row["総合コメント"] = overall
    return row

# 3. API関連関数 ---------------------------------------

def search_videos(query, max_results=6, page_token=None):
    try:
        req = youtube.search().list(
            part="snippet", q=query, type="video",
            videoEmbeddable="true", maxResults=max_results, order="relevance",
            pageToken=page_token 
        )
        res = req.execute()
    except Exception as e:
        st.error(f"検索エラー: {e}")
        return [], None
    
    results = []
    for item in res.get("items", []):
        vid = item.get("id", {}).get("videoId")
        if not vid: continue
        snip = item.get("snippet", {})
        results.append({
            "title": snip.get("title"),
            "video_id": vid,
            "thumbnail": snip.get("thumbnails", {}).get("medium", {}).get("url")
        })
    
    next_token = res.get("nextPageToken")
    return results, next_token

# 【修正】120件取得するループ処理（100件表示の予備のため）
def get_comments(video_id, max_comments=120):
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100, # APIの1ページ最大数
            textFormat="plainText",
            order="relevance"
        )
        while request and len(comments) < max_comments:
            response = request.execute()
            for item in response.get("items", []):
                try:
                    c = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                    comments.append(c)
                    if len(comments) >= max_comments:
                        break
                except KeyError:
                    continue
            
            # まだ足りなければ次ページへ
            if len(comments) < max_comments:
                request = youtube.commentThreads().list_next(request, response)
            else:
                break
    except Exception as e:
        st.warning(f"コメント取得エラー: {e}")
        return []
    return comments[:max_comments]

# 【修正】プロンプトのみ緩和版に変更（処理ロジックは旧コードのまま）
def analyze_comment(comment_text):
    prompt = f"""
    あなたはYouTubeコメントを分析する専門家です。
    以下のルールに【厳密に】従って、指定されたYouTubeコメントを6つの特徴量で分析し、JSON形式で出力してください。
    文脈や皮肉（反語）も考慮して評価してください。

    # 分析ルール（評価基準の緩和版）

    ## 1. 攻撃性 (Aggressiveness)
    - **0: なし**: 敬意がある、または中立的。
    - **1: 低**: 小馬鹿にする、見下すような表現。軽い不快感。
    - **2: 中**: 明確な悪口、強い嘲笑。「バカ」「ゴミ」などの侮辱語。
    - **3: 高**: **非常に激しい敵意、人格否定、または執拗な攻撃。**

    ## 2. 挑発性 (Provocation)
    - **0: なし**: 誠実でストレートな表現。
    - **1: 低**: 軽度の皮肉や嫌味。
    - **2: 中**: 上から目線、レッテル貼り。
    - **3: 高**: **相手を激昂させることを主目的とした強い煽り、悪質な嘲笑。**

    ## 3. 有用性 (Usefulness)
    - **0: なし**: 中身のない相槌、単なる感情表現。
    - **1: 低**: 根拠のない個人の感想。
    - **2: 中**: 具体的な指摘、改善提案、理由を伴う意見。
    - **3: 高**: **非常に論理的で、具体的な根拠や独自の深い視点に基づき、議論に貢献する極めて有益なコメント。**

    ## 4. 感情極性 (Sentiment Polarity)
    - **-2: 強いネガティブ**: 激怒、強い憎しみ。
    - **-1: ネガティブ**: 批判、不満。
    - **0: 中立**: 事実の記述。
    - **+1: ポジティブ**: 好意、感謝。
    - **+2: 強いポジティブ**: 感動、絶賛。

    ## 5. 自己顕示性 (Self-display)
    - **0: なし**: アピールなし。
    - **1: 低**: 文脈に沿った体験談。
    - **2: 中**: 知識ひけらかし、暗黙のマウント。
    - **3: 高**: **露骨なマウント、見下し。**

    ## 6. 文脈依存性 (Context-dependency)
    - **0: なし**: 誰でもわかる。
    - **1: 低**: 推測可能。
    - **2: 中**: ファン用語、ミーム。
    - **3: 高**: **深い知識がないと意味不明。**

    最後に総合コメントとして、評価理由を簡潔に説明してください。

    # 出力フォーマット（JSON）
    必ず **有効なJSON形式** で出力してください。
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
            messages=[{"role":"user", "content": prompt}],
            temperature=0.2
        )
        raw = resp.choices[0].message.content.strip()
        
        # 【旧コードと同じシンプルな処理に戻す】
        # 複雑な正規表現などはやめ、確実に動いていた時の処理だけにする
        raw = re.sub(r"```json", "", raw)
        raw = re.sub(r"```", "", raw)
        raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw_output": raw}
    except Exception as e:
        return {"error": str(e)}

# 4. サイドバー設定 ---------------------------------------
st.sidebar.header("🔧 フィルタ（閾値レンジ）設定")

preset = st.sidebar.radio("プリセットを選ぶ", ["フィルタなし", "平和モード", "議論モード", "カスタム"], index=0)

if preset == "フィルタなし":
    preset_ranges = {
        "攻撃性": (0,3), "挑発性": (0,3), "有用性": (0,3), "感情極性": (-2,2),
        "自己顕示性": (0,3), "文脈依存性": (0,3)
    }
elif preset == "平和モード":
    preset_ranges = {
        "攻撃性": (0,1), "挑発性": (0,1), "有用性": (0,3), "感情極性": (0,2),
        "自己顕示性": (0,3), "文脈依存性": (0,3)
    }
elif preset == "議論モード":
    preset_ranges = {
        "攻撃性": (0,2), "挑発性": (0,2), "有用性": (1,3), "感情極性": (-2,2),
        "自己顕示性": (0,3), "文脈依存性": (0,3)
    }
else:
    preset_ranges = {f["key"]:(f["min"], f["max"]) for f in FEATURES}

# 【修正】カスタム以外はスライダーを操作不可にする
is_disabled = (preset != "カスタム")

threshold_ranges = {}
with st.sidebar.expander("各特徴量の説明と閾値設定（範囲）", expanded=True):
    for f in FEATURES:
        key = f["key"]
        st.markdown(f"**{key}** — {f['desc']}")
        min_v, max_v = f["min"], f["max"]
        init_min, init_max = preset_ranges.get(key, (min_v, max_v))
        
        # disabledパラメータを追加
        rng = st.slider(
            f"{key} の許容レンジ", 
            min_v, max_v, 
            (init_min, init_max),
            disabled=is_disabled
        )
        threshold_ranges[key] = rng

# 5. メインロジック ------------------------------

if "selected_video_id" not in st.session_state:
    st.session_state["selected_video_id"] = None
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []
if "next_page_token" not in st.session_state:
    st.session_state["next_page_token"] = None

# 【シーン1】動画未選択時（検索画面）
if st.session_state["selected_video_id"] is None:
    st.markdown("### 1. 動画を検索")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("キーワードを入力", value="", label_visibility="collapsed", placeholder="例: AI 解説")
    with col2:
        search_btn = st.button("検索", use_container_width=True)
    
    if search_btn and query:
        st.session_state["search_results"] = []
        st.session_state["next_page_token"] = None
        results, token = search_videos(query, max_results=12) 
        st.session_state["search_results"] = results
        st.session_state["next_page_token"] = token

    if st.session_state["search_results"]:
        videos = st.session_state["search_results"]
        st.markdown(f"#### 検索結果 ({len(videos)}件 表示中)")
        
        N_COLS = 3
        for i in range(0, len(videos), N_COLS):
            cols = st.columns(N_COLS)
            for j in range(N_COLS):
                if i + j < len(videos):
                    v = videos[i + j]
                    with cols[j]:
                        if v["thumbnail"]:
                            st.image(v["thumbnail"], use_container_width=True)
                        title_disp = v["title"]
                        if len(title_disp) > 30: title_disp = title_disp[:30] + "..."
                        st.caption(title_disp)
                        
                        # 【修正】重複エラー対策（keyにindexを追加）
                        if st.button("選択", key=f"select_{v['video_id']}_{i+j}"):
                            st.session_state["selected_video_id"] = v["video_id"]
                            st.session_state["selected_title"] = v["title"]
                            st.rerun()

        if st.session_state["next_page_token"]:
            st.divider()
            if st.button("⬇️ もっと動画を読み込む"):
                new_results, new_token = search_videos(
                    query, max_results=12, page_token=st.session_state["next_page_token"]
                )
                if new_results:
                    st.session_state["search_results"].extend(new_results)
                    st.session_state["next_page_token"] = new_token
                    st.rerun()

# 【シーン2】動画選択後（分析画面）
else:
    vid = st.session_state["selected_video_id"]
    st.button("🔙 検索に戻る", on_click=lambda: st.session_state.update({"selected_video_id": None}))
    st.markdown(f"### 🎞️ 選択中: {st.session_state.get('selected_title','(no title)')}")
    st.video(f"https://www.youtube.com/watch?v={vid}")

    if st.button("💬 コメント分析を実行（上限100件）"):
        with st.spinner("コメントを取得してGPTで分析しています...（数十秒〜数分）"):
            # 120件取得
            comments = get_comments(vid, max_comments=120)
            if not comments:
                st.error("コメントを取得できませんでした（コメント無効またはAPI制限の可能性）")
            else:
                rows = []
                progress_bar = st.progress(0)
                
                # 並列処理（旧コードと同じWorker 10, エラーはpass）
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_comment = {executor.submit(analyze_comment, c): c for c in comments}
                    
                    for i, future in enumerate(concurrent.futures.as_completed(future_to_comment)):
                        c = future_to_comment[future]
                        try:
                            analysis = future.result()
                            row = normalize_analysis_to_row(analysis)
                            row["コメント"] = c
                            rows.append(row)
                        except Exception as e:
                            pass 
                        
                        progress_bar.progress((i + 1) / len(comments))

                df = pd.DataFrame(rows)
                st.session_state["analysis_df_raw"] = df
                
                # 【修正】120件取れても表示は「100件」に見せる
                display_msg_len = min(len(df), 100)
                st.success(f"{display_msg_len} 件のコメントを分析しました。")

# 6. 結果表示 ---------------------------------
if "analysis_df_raw" in st.session_state and st.session_state["analysis_df_raw"] is not None:
    df_raw = st.session_state["analysis_df_raw"]
    df = df_raw.copy()

    mask = pd.Series([True] * len(df))
    for f in FEATURES:
        key = f["key"]
        score_col = f"{key}_score"
        low, high = threshold_ranges.get(key, (f["min"], f["max"]))
        if score_col in df.columns:
            s = pd.to_numeric(df[score_col], errors="coerce")
            # 【修正】NaNも表示候補に残す（エラーで消えないようにする）
            mask &= s.isna() | ((s >= float(low)) & (s <= float(high)))
        else:
            mask &= True
    df_filtered = df[mask]

    # 【修正】表示データフレームを先頭100件に絞る
    if len(df_filtered) > 100:
        df_filtered = df_filtered.head(100)

    # 件数表示の分母も100に合わせる
    display_count = len(df_filtered)
    total_display_count = min(len(df), 100)

    st.markdown(f"**表示件数:** {display_count} / {total_display_count} 件（閾値レンジで絞り込み）")

    display_cols = ["コメント"] + [f"{f['key']}_score" for f in FEATURES] + ["総合コメント"]
    display_cols = [c for c in display_cols if c in df_filtered.columns]
    
    # 【改善】インデックスを1から開始
    if len(df_filtered) > 0:
        df_display = df_filtered[display_cols].reset_index(drop=True)
        df_display.index = df_display.index + 1
        st.dataframe(df_display, use_container_width=True)

        st.download_button(
            "💾 フィルタ結果をCSVでダウンロード",
            df_filtered.to_csv(index=False).encode("utf-8"),
            file_name="filtered_comment_analysis.csv",
            mime="text/csv"
        )
    else:
        st.warning("条件に合うコメントがありませんでした。")
