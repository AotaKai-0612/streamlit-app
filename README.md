# 🎥 YouTubeコメント分析アプリ（YouTube Comment Analysis App）

このリポジトリは、**YouTubeのコメントをAIで自動分析・可視化するWebアプリ**のソースコードです。  
YouTube Data API と OpenAI API（gpt-4o-mini）を組み合わせ、  
コメントの **攻撃性・挑発性・有用性・感情極性・自己顕示性・文脈依存性** の6項目を数値化します。

---

## 🌐 公開URL / Live Demo
🔗 **Streamlit App:** [https://aotakai-0612-youtube-comment-analysis.streamlit.app/](https://aotakai-0612-youtube-comment-analysis.streamlit.app/)  
💻 **Source Code (GitHub):** [https://github.com/AotaKai-0612/streamlit-app](https://github.com/AotaKai-0612/streamlit-app)

---

## 🚀 アプリ概要 / Overview
- YouTubeの動画タイトルまたはキーワードで検索  
- 対象動画のコメントを自動取得（最大50件）  
- 各コメントをGPTモデルで分析し、6つの観点でスコアリング  
- 結果を表形式で可視化・フィルタリング可能  
- CSV出力にも対応  

このアプリは、**SNS上のコメント評価や皮肉検出研究**にも活用できる設計です。

---

## 🧩 主なファイル / Main Files

| ファイル名 | 内容 |
|-------------|------|
| `app.py` | Streamlitで構築したWebアプリ本体（UI付きで実行可能） |
| `analyze_video_comments.py` | 同じ分析処理をコマンドラインから一括実行できる研究用スクリプト |
| `requirements.txt` | 使用するPythonライブラリの一覧 |

---

## ⚙️ 使用技術 / Tech Stack
- **Language:** Python  
- **Framework:** Streamlit  
- **APIs:** YouTube Data API, OpenAI API  
- **Libraries:** pandas, google-api-python-client, tqdm, python-dotenv  

---

## 💡 実行方法 / How to Run Locally
```bash
git clone https://github.com/AotaKai-0612/streamlit-app.git
cd streamlit-app
pip install -r requirements.txt
streamlit run app.py
