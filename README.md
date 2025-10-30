# 🎥 YouTubeコメント分析アプリ（YouTube Comment Analysis App）

このリポジトリは、YouTubeコメントをAIで多角的に分析・可視化するWebアプリのソースコードです。  
YouTube Data API と OpenAI API（gpt-4o-mini）を組み合わせ、  
コメントの **攻撃性・挑発性・有用性・感情極性・自己顕示性・文脈依存性** の6項目を自動スコアリングします。

---

## 🌐 公開URL
- Streamlitアプリ: [https://aotakai-0612-youtube-comment-analysis.streamlit.app/](https://aotakai-0612-youtube-comment-analysis.streamlit.app/)
- ソースコード(GitHub): [https://github.com/AotaKai-0612/streamlit-app](https://github.com/AotaKai-0612/streamlit-app)

---

## 🎓 学部研究
**テーマ：「YouTubeにおける皮肉コメントの検出」**

ネット上の誹謗中傷は巧妙化しており、既存システムでは検知できない「皮肉」による中傷が問題となっていました。  
世界最大級の動画サービスで多様な表現が集まるYouTubeは、この課題の研究に適していると考えました。  
最大の課題は、皮肉の定義が人によって異なるという主観性の強さでした。  
そこで10名の被験者にアンケートを行い、多様な評価を収集してラベルの妥当性を高めました。  
また、ルールベース手法と機械学習（BERT）を組み合わせたハイブリッドモデルを考案し、  
単独手法で正解率60%だった精度を88%まで向上させました。

---

## 🎓 修士研究
**テーマ：「ユーザのニーズに応じたYouTubeコメントフィルタリングシステム」**

学部研究で直面した「同じコメントでも人によって捉え方が変わる」という課題に対し、  
単なる二値分類では不十分だと考え、LLM（GPT-4）を用いた多次元スコアリングモデルを構築しました。  
コメントを「攻撃性」「有用性」など6つの評価軸でスコアリングし、  
ユーザが「閲覧したい／したくない」コメントを選択すると、  
選択結果から各特徴量の許容度を算出して個別基準でフィルタリングを行う仕組みを実装しました。  
この開発を通じて、LLMのプロンプト設計と実装力を高めました。

---

## 🚀 アプリ概要
- YouTube動画を検索し、コメントを自動取得（最大50件）  
- GPTモデルによる6軸スコアリングと総合コメント生成  
- スライダーで閾値を設定し、コメントを絞り込み  
- 結果を表形式で可視化・CSVでダウンロード可能  

このアプリは修士研究のシステムをWeb上で再現したものです。

---

## 🧩 ファイル構成

| ファイル名 | 内容 |
|-------------|------|
| `app.py` | Streamlitアプリ本体（ブラウザ上で動作） |
| `analyze_video_comments.py` | コメントを一括分析してCSV出力するスクリプト |
| `requirements.txt` | 使用ライブラリ一覧 |

---

## ⚙️ 使用技術
- Python  
- Streamlit  
- YouTube Data API  
- OpenAI API  
- pandas / google-api-python-client / tqdm / python-dotenv  

---

## 💡 実行方法
```bash
git clone https://github.com/AotaKai-0612/streamlit-app.git
cd streamlit-app
pip install -r requirements.txt
streamlit run app.py

pip install -r requirements.txt
streamlit run app.py

