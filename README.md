# ai-article-arranger

FastAPI + HTMX で作った、元記事と検索上位記事の傾向をもとに新しい記事案を生成するMVPです。競合記事はコピー対象ではなく、検索意図と不足トピックを見つけるための材料としてだけ使います。

## アプリ概要

- 入力: 元記事URL、対策キーワード、追加プロンプト
- 処理: 元記事取得、競合検索、上位記事分析、記事生成、類似度チェック、DB保存
- 出力: タイトル、メタディスクリプション、見出し構成、Markdown本文、FAQ、コピー回避メモ

## 技術スタック

- Python 3.11+
- FastAPI
- HTMX
- Jinja2
- SQLAlchemy
- SQLite
- httpx
- BeautifulSoup4
- trafilatura
- OpenAI API
- Tailwind CSS CDN
- Render Free Plan

## セットアップ方法

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## .env 設定

最低限は以下です。

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
SEARCH_PROVIDER=mock
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_ENGINE_ID=
SERPAPI_API_KEY=
DATABASE_URL=sqlite:///./app.db
```

ローカルで API を使わず画面確認だけしたい場合は `OPENAI_MODEL=mock` にすると、モック生成で最後まで動かせます。

## ローカル起動方法

```bash
uvicorn app.main:app --reload
```

Makefile を使う場合は次で足ります。

```bash
make setup
make run
```

ブラウザで `http://127.0.0.1:8000/` を開きます。

モックだけで一連の動作を試す場合は次の入力例が使えます。

- 元記事URL: `https://example.com/mock/original`
- 対策キーワード: `SEO 記事 リライト`
- 追加プロンプト: 任意

## Render デプロイ方法

1. GitHub リポジトリを Render に接続します。
2. ルートの `render.yaml` を使って Web Service を作成します。
3. `OPENAI_API_KEY` を Render の環境変数に設定します。
4. 検索 API を使う場合は `SEARCH_PROVIDER` と対応する API キーも設定します。

SQLite は Render Free Plan では永続化に向かないため、本番運用では外部DBへの移行を前提にしてください。

## 検索APIの切り替え方法

- `SEARCH_PROVIDER=mock`
  ローカル確認向けです。固定の上位3記事を返します。
- `SEARCH_PROVIDER=ddgs`
  APIキー不要で検索できます。検索結果は `ddgs`、本文抽出は `trafilatura` を使います。
- `SEARCH_PROVIDER=google`
  `GOOGLE_SEARCH_API_KEY` と `GOOGLE_SEARCH_ENGINE_ID` が必要です。
- `SEARCH_PROVIDER=serpapi`
  `SERPAPI_API_KEY` が必要です。

## 注意点

- 背景処理は FastAPI の `BackgroundTasks` なので、単一プロセス前提の軽量MVPです。
- `OPENAI_API_KEY` 未設定で `OPENAI_MODEL` が通常モデルのままだと、ジョブ作成時にエラー表示します。
- 一部サイトはbot対策や利用規約により本文取得に失敗することがあります。
- `ddgs` は無料で便利ですが、検索結果の安定性は正式APIより弱いです。
- SQLite を使っているため、複数ワーカー構成や高負荷運用には向きません。

## コピーコンテンツ回避の設計思想

- 競合記事本文は LLM プロンプトに渡さず、タイトル、URL、見出し、要約、不足トピックだけを渡します。
- 競合の構成を丸ごと模倣せず、元記事に不足する観点だけを補う設計です。
- 生成後に `difflib.SequenceMatcher` で元記事と競合記事との類似度を計算します。
- 連続一致フレーズの簡易チェックと、コピー回避メモを結果に保存します。

## テストと確認コマンド

```bash
python -m compileall app
pytest
uvicorn app.main:app --reload
```

Makefile の便利コマンド:

```bash
make help
make run
make run-mock
make test
make check
make mock-request
```

## ディレクトリ概要

```txt
app/
  core/       設定とログ
  db/         SQLAlchemyモデルとCRUD
  routes/     FastAPIルーティング
  schemas/    Pydanticスキーマ
  services/   取得、検索、分析、生成、類似度チェック
  templates/  Jinja2 + HTMX UI
  static/     追加CSS
prompts/      LLM用YAMLプロンプト
tests/        最低限の単体テスト
```
