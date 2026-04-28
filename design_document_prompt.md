# Codex実装依頼プロンプト: FastAPI + HTMX 記事生成AIアプリ

あなたはシニアフルスタックエンジニアです。  
以下の要件に従って、FastAPI + HTMX を使った記事生成AIアプリを実装してください。

目的は、ユーザーが入力した「元記事URL」「対策キーワード」「追加プロンプト」をもとに、元記事をベースにしながら、検索上位記事の傾向を参考にして、コピーコンテンツにならない新しい記事を生成するWebアプリを作ることです。

---

## 1. アプリ概要

### アプリ名

`ai-article-arranger`

### 技術スタック

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
- Render Free Plan へのデプロイ想定

---

## 2. 実現したい機能

ユーザーが画面から以下を入力する。

- 元記事URL
- 対策キーワード
- 追加プロンプト

アプリは以下を実行する。

1. 元記事URLから本文を取得する
2. 対策キーワードで検索APIを使って検索する
3. SEO上位3記事の情報を取得する
4. 上位記事から以下を抽出する
   - タイトル
   - URL
   - 見出し構成
   - 主要トピック
   - 元記事に足りない観点
5. 元記事をベースに、コピーコンテンツにならないように新しい記事を生成する
6. 表、箇条書き、FAQ、比較リストなどを追加する
7. 結果を画面に表示する
8. 生成結果をDBに保存する

---

## 3. 重要な設計方針

このアプリは、競合記事をコピーするアプリではありません。  
競合記事はあくまで以下の目的で使用します。

- 検索意図の把握
- 読者ニーズの把握
- 元記事に不足している情報の発見
- 見出し構成の参考
- FAQ候補の発見

以下は禁止です。

- 競合記事の文章をそのままコピーする
- 競合記事の構成を丸ごと真似する
- 競合記事の表現、語順、例文をそのまま使う
- 元記事を少しだけ言い換えただけの記事を出す

生成記事には以下を必ず含めてください。

- 独自タイトル
- メタディスクリプション
- h2 / h3構成
- 本文
- 比較表または整理表
- 箇条書き
- FAQ 3つ以上
- コピー回避のために行った工夫

---

## 4. 画面仕様

### トップページ `/`

入力フォームを表示する。

フォーム項目:

- 元記事URL
- 対策キーワード
- 追加プロンプト
- 生成ボタン

送信はHTMXで行う。

```html
<form hx-post="/jobs" hx-target="#job-area" hx-swap="innerHTML">
```

### ジョブステータス画面

ジョブ作成後、以下のような状態を表示する。

- queued
- fetching_original
- searching
- fetching_competitors
- analyzing
- generating
- checking
- completed
- failed

HTMXで数秒ごとに `/jobs/{job_id}/status` をポーリングする。

### 結果画面

生成完了後に以下を表示する。

- タイトル
- メタディスクリプション
- 見出し構成
- 生成本文Markdown
- FAQ
- コピー回避メモ
- 参考にした上位記事一覧

Markdown本文は `<textarea>` にも表示し、コピーしやすくする。

---

## 5. ディレクトリ構成

以下の構成で実装してください。

```txt
ai-article-arranger/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── db/
│   │   ├── session.py
│   │   ├── models.py
│   │   └── crud.py
│   ├── schemas/
│   │   ├── article.py
│   │   └── job.py
│   ├── services/
│   │   ├── article_fetcher.py
│   │   ├── serp_search.py
│   │   ├── content_extractor.py
│   │   ├── seo_analyzer.py
│   │   ├── prompt_builder.py
│   │   ├── article_generator.py
│   │   ├── similarity_checker.py
│   │   └── article_pipeline.py
│   ├── routes/
│   │   ├── pages.py
│   │   └── jobs.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── job_created.html
│   │   ├── job_status.html
│   │   └── result.html
│   └── static/
│       └── css/
│           └── app.css
├── prompts/
│   └── article_rewrite.yaml
├── tests/
├── .env.example
├── requirements.txt
├── render.yaml
├── README.md
└── .gitignore
```

---

## 6. DB設計

SQLiteで実装してください。  
SQLAlchemy ORMを使用してください。

### article_jobs

| column | type | description |
|---|---|---|
| id | string | UUID |
| original_url | string | 元記事URL |
| target_keyword | string | 対策キーワード |
| user_prompt | text | 追加プロンプト |
| status | string | ジョブ状態 |
| error_message | text nullable | エラー内容 |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

### competitor_articles

| column | type | description |
|---|---|---|
| id | string | UUID |
| job_id | string | article_jobs.id |
| rank | integer | 検索順位 |
| url | string | 競合記事URL |
| title | string | タイトル |
| headings_json | text | 見出しJSON |
| summary | text | 要約 |
| extracted_text | text | 抽出本文 |
| created_at | datetime | 作成日時 |

### generated_articles

| column | type | description |
|---|---|---|
| id | string | UUID |
| job_id | string | article_jobs.id |
| title | string | 生成タイトル |
| meta_description | text | メタディスクリプション |
| outline_json | text | 見出し構成JSON |
| article_markdown | text | 生成本文Markdown |
| article_html | text | 生成本文HTML |
| faq_json | text | FAQ JSON |
| copy_check_json | text | コピー回避チェックJSON |
| created_at | datetime | 作成日時 |

---

## 7. ルーティング設計

### pages.py

```txt
GET /
```

トップページを返す。

### jobs.py

```txt
POST /jobs
GET /jobs/{job_id}
GET /jobs/{job_id}/status
GET /jobs/{job_id}/result
```

#### POST /jobs

フォームから受け取った内容でジョブを作成する。  
BackgroundTasksで記事生成処理を開始する。  
`job_created.html` を返す。

#### GET /jobs/{job_id}/status

ジョブ状態をHTML partialとして返す。  
completedなら結果取得リンクまたは結果表示に切り替える。

#### GET /jobs/{job_id}/result

生成済み記事を表示する。

---

## 8. サービス設計

### article_fetcher.py

URLからHTMLを取得する。

要件:

- httpxを使う
- timeoutを設定する
- User-Agentを設定する
- 失敗時は例外を出す

### content_extractor.py

HTMLから本文を抽出する。

優先順位:

1. trafilatura
2. BeautifulSoup fallback

抽出対象:

- title
- h1
- h2
- h3
- main text

### serp_search.py

検索APIを抽象化する。

最初は以下のどちらかで実装する。

- Google Custom Search API
- SerpAPI

環境変数で切り替えられるようにする。

`.env.example` に以下を含める。

```env
OPENAI_API_KEY=
SEARCH_PROVIDER=mock
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_ENGINE_ID=
SERPAPI_API_KEY=
DATABASE_URL=sqlite:///./app.db
```

開発しやすいように、`SEARCH_PROVIDER=mock` の場合は固定の検索結果を返す実装も用意してください。

### seo_analyzer.py

元記事と競合記事を分析する。

抽出する情報:

- 見出し一覧
- 共通トピック
- 元記事に不足している観点
- 追加すべき表
- 追加すべきFAQ

最初はルールベースでよいです。  
LLMを使う必要はありません。

### prompt_builder.py

LLMに渡すプロンプトを組み立てる。

競合記事本文を丸ごと渡さないでください。  
以下だけ渡してください。

- title
- url
- headings
- summary
- missing topics

### article_generator.py

OpenAI APIを使って記事を生成する。

要件:

- JSON形式で出力させる
- JSONパースに失敗した場合のfallbackを実装する
- モデル名は環境変数で指定できるようにする

環境変数:

```env
OPENAI_MODEL=gpt-4.1-mini
```

出力JSON形式:

```json
{
  "title": "...",
  "meta_description": "...",
  "outline": [
    {"level": 2, "heading": "..."},
    {"level": 3, "heading": "..."}
  ],
  "article_markdown": "...",
  "faq": [
    {"question": "...", "answer": "..."}
  ],
  "copy_avoidance_notes": ["..."]
}
```

### similarity_checker.py

最低限、以下を実装する。

- 元記事と生成記事の類似度
- 競合記事と生成記事の類似度
- 連続一致フレーズの簡易チェック

`difflib.SequenceMatcher` でよいです。

返却形式:

```json
{
  "original_similarity": 0.42,
  "max_competitor_similarity": 0.31,
  "risk_level": "low",
  "notes": ["..."]
}
```

### article_pipeline.py

記事生成全体を実行する。

処理順:

```txt
1. job status = fetching_original
2. 元記事取得
3. job status = searching
4. 検索API実行
5. job status = fetching_competitors
6. 上位3記事取得
7. job status = analyzing
8. SEO分析
9. job status = generating
10. LLMで記事生成
11. job status = checking
12. 類似度チェック
13. 結果保存
14. job status = completed
```

失敗時:

```txt
job status = failed
error_message に内容を保存
```

---

## 9. プロンプトファイル

`prompts/article_rewrite.yaml` を作成してください。

内容:

```yaml
system: |
  あなたはSEO編集者兼Webライターです。
  元記事をベースに、検索意図を満たす高品質な記事へ再構成してください。
  競合記事の文章、構成、語順、例文をコピーしてはいけません。
  競合記事は、読者ニーズと不足トピックを把握するためだけに使用してください。

user: |
  # 目的
  元記事を、対策キーワードで上位表示を狙える記事にアレンジしてください。

  # 対策キーワード
  {{ target_keyword }}

  # 元記事
  {{ original_article }}

  # 競合記事の分析情報
  {{ competitor_insights }}

  # 追加指示
  {{ user_prompt }}

  # 必須条件
  - 競合記事の文章をコピーしない
  - 元記事の単純な言い換えだけにしない
  - 表を最低1つ入れる
  - 箇条書きを複数入れる
  - FAQを3つ以上入れる
  - 読者の検索意図に答える
  - メタディスクリプションは100〜120文字程度にする
  - Markdown形式の記事本文を作る

  # 出力形式
  以下のJSONのみを返してください。

  {
    "title": "...",
    "meta_description": "...",
    "outline": [
      {"level": 2, "heading": "..."},
      {"level": 3, "heading": "..."}
    ],
    "article_markdown": "...",
    "faq": [
      {"question": "...", "answer": "..."}
    ],
    "copy_avoidance_notes": ["..."]
  }
```

---

## 10. UIデザイン方針

Tailwind CSS CDNを使い、最低限モダンなUIにしてください。

要件:

- 中央寄せのカードUI
- 入力フォームは見やすく
- 生成中はステータス表示
- 完了時は結果カード表示
- Markdown本文は大きなtextareaで表示
- エラー時は赤色のアラート表示

---

## 11. requirements.txt

以下を含めてください。

```txt
fastapi
uvicorn[standard]
jinja2
python-multipart
sqlalchemy
pydantic-settings
httpx
beautifulsoup4
trafilatura
python-dotenv
openai
pyyaml
markdown
```

---

## 12. render.yaml

Render Free Planにデプロイできるように作成してください。

```yaml
services:
  - type: web
    name: ai-article-arranger
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: OPENAI_API_KEY
        sync: false
      - key: OPENAI_MODEL
        value: gpt-4.1-mini
      - key: SEARCH_PROVIDER
        value: mock
      - key: DATABASE_URL
        value: sqlite:///./app.db
```

---

## 13. README.md

READMEには以下を含めてください。

- アプリ概要
- 技術スタック
- セットアップ方法
- .env設定
- ローカル起動方法
- Renderデプロイ方法
- 検索APIの切り替え方法
- 注意点
- コピーコンテンツ回避の設計思想

---

## 14. .gitignore

以下を含めてください。

```gitignore
.env
__pycache__/
*.pyc
app.db
.venv/
.DS_Store
```

---

## 15. バリデーション

入力バリデーションを実装してください。

- original_url はURL形式
- target_keyword は空禁止
- user_prompt は任意
- URL取得に失敗した場合はわかりやすいエラーを表示
- OPENAI_API_KEYが未設定の場合もエラー表示

---

## 16. エラーハンドリング

以下のケースに対応してください。

- 元記事URLが取得できない
- 本文抽出に失敗する
- 検索APIが失敗する
- 競合記事が取得できない
- OpenAI APIが失敗する
- JSONパースに失敗する
- DB保存に失敗する

ユーザー画面には、技術的すぎないエラーを表示してください。  
ログには詳細を出してください。

---

## 17. テスト

最低限、以下のテストを作成してください。

```txt
tests/test_similarity_checker.py
tests/test_seo_analyzer.py
tests/test_prompt_builder.py
```

---

## 18. 完成条件

以下を満たしたら完成です。

- `uvicorn app.main:app --reload` で起動できる
- `/` にアクセスしてフォームが表示される
- フォーム送信でジョブが作成される
- ステータスがHTMXで更新される
- mock検索モードで記事生成まで実行できる
- 生成結果が画面に表示される
- 生成結果がDBに保存される
- READMEの手順通りにセットアップできる
- Renderにデプロイ可能な構成になっている

---

## 19. 実装時の注意

- まずMVPとして動くものを優先してください
- 過度に複雑なCeleryやRedisは使わないでください
- Render無料枠で動く軽量構成にしてください
- 検索APIはmockモードを必ず用意してください
- DBはSQLiteで開始してください
- コードには日本語コメントを適度に入れてください
- 関数は責務ごとに分けてください
- サービス層を厚めにして、routesにロジックを書きすぎないでください

---

## 20. 最後に実行してほしい確認コマンド

実装後、以下を実行して問題がないか確認してください。

```bash
python -m compileall app
pytest
uvicorn app.main:app --reload
```

起動確認後、READMEに従って使える状態にしてください。
