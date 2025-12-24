# 🛡️ YouTube Comment Analysis & Filtering System
**多次元評価を用いたYouTubeコメントのユーザ適応型フィルタリング**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://aotakai-0612-youtube-comment-analysis.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![OpenAI](https://img.shields.io/badge/LLM-GPT--4o--mini-green)
![YouTube API](https://img.shields.io/badge/API-YouTube%20Data%20v3-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🔗 Links
- **🚀 Live App (Demo):** [https://aotakai-0612-youtube-comment-analysis.streamlit.app/](https://aotakai-0612-youtube-comment-analysis.streamlit.app/)
- **💻 Source Code:** [https://github.com/AotaKai-0612/streamlit-app](https://github.com/AotaKai-0612/streamlit-app)

---

## 📖 概要 (Overview)
YouTubeコメント欄における「不快感」の基準は主観的であり、従来の一律的なキーワードフィルタリングでは不十分です。
本アプリケーションは、**LLM（GPT-4o-mini）を用いた多次元評価**により、コメントを「攻撃性」「有用性」など6つの軸で定量的にスコアリング。
ユーザごとの許容度（閾値）に応じた**「個人の価値観に寄り添うフィルタリング」**を実現するプロトタイプシステムです。

---

## 🎓 研究背景 (Research Background)

本プロジェクトは、学部時代からの研究を基盤として開発されています。

### 1. 学部研究：主観性の壁への挑戦
**テーマ：「YouTubeにおける皮肉コメントの検出」**
ネット上の誹謗中傷は巧妙化しており、既存システムでは検知できない「皮肉（Sarcasm）」による中傷が社会問題となっていました。
私は世界最大級の動画プラットフォームであるYouTubeを対象に、この課題に取り組みました。

* **課題**: 皮肉の定義は人によって異なり、教師データのラベル基準統一が困難（主観性の壁）。
* **アプローチ**: 10名の被験者へのアンケート調査を実施し、多様な評価を収集してラベルの妥当性を検証。
* **成果**: ルールベースと機械学習（BERT）を組み合わせた独自のハイブリッドモデルを考案。単独手法で60%だった正解率を**88%**まで向上させました。

### 2. 修士研究：適応型フィルタリングへの進化
**テーマ：「ユーザのニーズに応じたYouTubeコメントフィルタリングシステム」**
学部研究で直面した「同じコメントでも人によって捉え方が変わる」という課題に対し、一律の判定ではなく「ユーザごとの最適化」が必要であると結論付けました。

* **解決策**: LLM（GPT-4）を活用し、単純なネガ/ポジ判定ではなく、多次元でのベクトル評価モデルを構築。
* **実装**: 本アプリでは「平和モード」「議論モード」などのプリセットに加え、ユーザ自身がスライダーで各特徴量の許容範囲を微調整できる機能を実装。「批判は見たいが、暴言は排除したい」といった微細なニーズに対応します。

---

## ✨ 主な機能 (Key Features)

### 📊 1. LLMによる6軸・多次元分析
GPT-4o-miniに対し、厳密な定義プロンプトを与えることで、以下の6項目を0〜3（または-2〜+2）のスケールでスコアリングします。

| 特徴量 | 説明 |
| :--- | :--- |
| **攻撃性 (Aggressiveness)** | 他者への直接的な敵意、侮辱、脅迫の度合い。 |
| **挑発性 (Provocation)** | 皮肉、嫌味、煽りなど、相手を感情的にさせる意図。 |
| **有用性 (Usefulness)** | 動画内容へのフィードバックや議論への貢献度。 |
| **感情極性 (Sentiment)** | 感情のトーン（強いネガティブ〜強いポジティブ）。 |
| **自己顕示性 (Self-display)** | マウント行為や知識のひけらかし度合い。 |
| **文脈依存性 (Context)** | 内輪ネタや専門用語など、背景知識の必要性。 |

### 🎚️ 2. ユーザ適応型フィルタリング (Custom Filtering)
ユーザの気分や目的に合わせて、表示するコメントを制御できます。
- **🕊️ 平和モード**: 攻撃性・挑発性を「0（なし）」のみに限定。精神的安全性を最優先します。
- **🗣️ 議論モード**: 多少の強い言葉は許容しつつ、有用性が高い意見を抽出します。
- **⚙️ カスタムモード**: 全パラメータの閾値をスライダーで自由に設定可能。

### 🚀 3. 技術的なこだわり（Performance & UX）
- **高速並列処理**: `concurrent.futures.ThreadPoolExecutor` を実装し、APIアクセスの待ち時間を最小化。数十〜百件のコメント分析をストレスなく実行します。
- **キャッシュ機構**: Streamlitの `@st.cache_resource` を活用し、APIクライアントの再生成や無駄なリクエストを防止。
- **データエクスポート**: 分析・フィルタリング後の結果をCSV形式でダウンロード可能。二次分析に活用できます。

---

## 📂 ファイル構成 (Directory Structure)

```text
.
├── app.py                     # Streamlitアプリ本体（UI構築, 並列処理, フィルタリングロジック）
├── analyze_video_comments.py  # コマンドライン用の一括分析スクリプト（CSV出力特化）
├── requirements.txt           # 依存ライブラリ一覧
├── .env                       # APIキー管理（Git管理対象外）
└── README.md                  # 本ドキュメント
🛠️ 使用技術 (Tech Stack)CategoryTechnologyDetailsFrontendStreamlitPythonのみで構築するインタラクティブWeb UILLM / AIOpenAI APIgpt-4o-mini (Temperature 0.2 / JSON Mode)Data SourceYouTube Data API v3動画メタデータおよびコメントの取得Data ProcessingPandas, RegexJSONデータの正規化、データフレーム操作Concurrencyconcurrent.futuresマルチスレッドによるAPIリクエスト並列化EnvironmentPython 3.9+, Dotenv環境変数の安全な管理💻 セットアップと実行 (Installation)ご自身のローカル環境で動作させる場合の手順です。リポジトリのクローンBashgit clone [https://github.com/AotaKai-0612/streamlit-app.git](https://github.com/AotaKai-0612/streamlit-app.git)
cd streamlit-app
依存関係のインストールBashpip install -r requirements.txt
環境変数の設定プロジェクト直下に .env ファイルを作成し、ご自身のAPIキーを設定してください。PlaintextYOUTUBE_API_KEY=your_youtube_api_key
OPENAI_API_KEY=your_openai_api_key
アプリの起動Bashstreamlit run app.py
