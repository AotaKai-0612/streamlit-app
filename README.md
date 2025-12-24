# 🛡️ YouTube Comment Analysis & Filtering System
**多次元評価を用いたYouTubeコメントのユーザ適応型フィルタリング**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://aotakai-0612-youtube-comment-analysis.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![OpenAI](https://img.shields.io/badge/LLM-GPT--4o--mini-green)
![YouTube API](https://img.shields.io/badge/API-YouTube%20Data%20v3-red)

## 📖 概要 (Overview)
YouTubeコメント欄の「不快感」は主観的であり、一律の基準では排除しきれません。
本アプリケーションは、**LLM（GPT-4o-mini）を用いた多次元評価**により、コメントを「攻撃性」「有用性」など6つの軸で定量化。
「平和モード」や「議論モード」など、**ユーザの許容度に応じた柔軟なフィルタリング**を実現するプロトタイプシステムです。

---

## 🎓 研究背景 (Research Background)

### 1. 学部研究：主観性の壁
**テーマ：「YouTubeにおける皮肉コメントの検出」**
ネット上の誹謗中傷における「皮肉（Sarcasm）」の検知に取り組みました。
BERTを用いたハイブリッドモデルにより検知精度を60%から**88%**へ向上させましたが、**「同じコメントでも人によって不快かどうかが異なる（主観性）」**という根本的な課題に直面しました。

### 2. 修士研究：個への適応（本システムのコンセプト）
**テーマ：「ユーザのニーズに応じたYouTubeコメントフィルタリングシステム」**
「一律の排除」から「個別の最適化」への転換を目指しました。
LLMを活用してコメントを単なる ネガ/ポジ ではなく、**6つの評価軸（攻撃性・挑発性・有用性・感情極性・自己顕示性・文脈依存性）** でベクトル化。
ユーザが自身の許容レベル（閾値）を設定することで、**「批判は見たいが、暴言は見たくない」といった微細なニーズ**に対応可能なシステムを構築しました。

---

## ✨ 主な機能 (Key Features)

### 📊 6軸による多次元分析
GPT-4o-miniに対し、詳細な定義プロンプトを与えることで以下のパラメータを算出します。
- **攻撃性 (Aggressiveness)**: 直接的な暴言、敵意。
- **挑発性 (Provocation)**: 皮肉、煽り、レッテル貼り。
- **有用性 (Usefulness)**: 議論への貢献度、論理性。
- **感情極性 (Sentiment)**: -2(強ネガ) 〜 +2(強ポジ)。
- **自己顕示性 (Self-display)**: マウント行為、知識のひけらかし。
- **文脈依存性 (Context-dependency)**: 内輪ネタ、専門用語の多さ。

### 🎚️ ユーザ適応型フィルタリング (Filtering Modes)
- **🕊️ 平和モード**: 攻撃性・挑発性を極限まで排除し、精神的安全性を確保。
- **🗣️ 議論モード**: 多少の言葉の強さは許容しつつ、有用性の高い意見を抽出。
- **⚙️ カスタムモード**: 全パラメータの閾値をユーザがスライダーで自由に調整可能。

### 🚀 高速な並列処理
- `concurrent.futures` を用いたマルチスレッド処理により、APIアクセスのレイテンシを最小化し、100件程度のコメントを高速に分析します。

---

## 🛠️ 技術スタック (Tech Stack)

| Category | Tech / Library | Details |
| --- | --- | --- |
| **Frontend** | Streamlit | インタラクティブなUI構築 |
| **LLM** | OpenAI API | `gpt-4o-mini` (Temperature 0.2) |
| **Data Source** | YouTube Data API v3 | コメント・動画情報の取得 |
| **Processing** | Pandas, Concurrent.futures | データ整形、並列処理 |
| **Environment** | Python 3.9+, Dotenv | 環境変数管理 |

---

## 📂 ディレクトリ構成

```text
.
├── app.py                     # Streamlitアプリ本体（UI, 並列処理ロジック）
├── analyze_video_comments.py  # コメント一括分析・CSV出力用スクリプト
├── requirements.txt           # 依存ライブラリ
├── .env                       # APIキー設定（git管理外）
└── README.md                  # 本ドキュメント
💻 セットアップと実行 (Installation)
ローカル環境で動作させる場合の手順です。

リポジトリのクローン

Bash

git clone [https://github.com/AotaKai-0612/streamlit-app.git](https://github.com/AotaKai-0612/streamlit-app.git)
cd streamlit-app
依存関係のインストール

Bash

pip install -r requirements.txt
環境変数の設定 .env ファイルを作成し、APIキーを設定してください。

Plaintext

YOUTUBE_API_KEY=your_youtube_api_key
OPENAI_API_KEY=your_openai_api_key
アプリの起動

Bash

streamlit run app.py
