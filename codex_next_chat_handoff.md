# Codex 引き継ぎ書

このファイルは、次の Codex チャットでこのリポジトリの作業を再開するための完全な引き継ぎ書です。

---

## 1. 現在の状態

- リポジトリ: `article-arrange-app`
- 現在ブランチ: `main`
- git 状態: clean
- 現在の HEAD: `367e7bc40277b2c6dbe0a717710e25c58f2e5f23`
- `origin/main` と同期済み

直近コミット:

- `367e7bc` Merge branch `main` of remote
- `63b9d8a` `OPENAI_MODEL` を `mock` に変更
- `5a18169` `feature/simplify-form-design` を `main` にマージ
- `63505cf` UI整理 + プロンプトテンプレート管理追加
- `b710749` `design_document_prompt.md` を追加

---

## 2. アプリの目的

FastAPI + HTMX で動く記事生成アプリ。

入力:

- 元記事URL
- 対策キーワード
- フロントエンドから変更できるジョブ設定

処理:

1. 元記事を取得
2. 検索結果を取得
3. 競合記事を取得
4. ルールベースでSEO分析
5. LLM用プロンプトを生成
6. 記事生成
7. 類似度チェック
8. DB保存

出力:

- HTMLプレビュー中心の結果表示
- HTMLダウンロード
- 折りたたみ式の詳細情報

---

## 3. 現在のUI方針

ユーザー要望により、UIは説明より作業性優先になっている。

### トップページ `/`

- 上段: 入力フォーム
- 下段: ジョブ進行状況 or 結果表示
- 左右2カラムではなく縦積み
- 追加プロンプト入力UIは削除済み
- 白黒基調のクラシック寄り配色
- フォントは元のサンセリフに戻してある

### ガイド `/guide`

- 簡易説明ページ
- 戻るボタンあり

### プロンプト管理 `/prompts`

- DB保存のプロンプトテンプレート一覧
- バージョン切替
- 編集
- 保存
- 複製して新バージョン作成
- 有効化

### 結果表示

- メインは HTMLプレビュー
- HTMLダウンロードボタンあり
- 以下は折りたたみ表示
  - 見出し構成とコピー回避チェック
  - FAQと参考記事
  - MarkdownとHTMLソース

---

## 4. 現在のルーティング

### `app/routes/pages.py`

- `GET /`
  - トップページ
- `GET /guide`
  - ガイドページ
- `GET /prompts`
  - プロンプト編集画面

### `app/routes/jobs.py`

- `POST /jobs`
  - ジョブ作成
- `GET /jobs/{job_id}`
  - ジョブ付きトップページ
- `GET /jobs/{job_id}/status`
  - HTMXポーリング用ステータス
- `GET /jobs/{job_id}/result`
  - 結果付きトップページ
- `GET /jobs/{job_id}/download`
  - 生成HTMLをダウンロード
- `POST /jobs/prompts`
  - プロンプト新規バージョン作成
- `POST /jobs/prompts/{template_id}`
  - プロンプト更新
- `POST /jobs/prompts/{template_id}/activate`
  - プロンプト有効化

---

## 5. 主要アーキテクチャ

### アプリ起動

- エントリ: `app/main.py`
- `lifespan` で `init_db()` を実行

### DB

- SQLAlchemy + SQLite
- セッション: `app/db/session.py`

### モデル

`app/db/models.py`

- `ArticleJob`
- `CompetitorArticle`
- `GeneratedArticle`
- `PromptTemplate`

### CRUD

`app/db/crud.py`

主な責務:

- ジョブ作成/取得/状態更新
- 競合記事保存
- 生成記事保存
- アクティブなプロンプト取得
- プロンプト一覧/更新/複製/有効化

### サービス

`app/services/`

- `article_fetcher.py`
  - HTML取得
  - mock URLの固定HTMLを返す経路あり
- `content_extractor.py`
  - `trafilatura` 優先 + BeautifulSoup fallback
- `serp_search.py`
  - `mock / google / serpapi`
- `seo_analyzer.py`
  - ルールベース分析
- `prompt_builder.py`
  - テンプレート文字列と差し込み変数から最終プロンプト組立
- `article_generator.py`
  - OpenAI or mock 記事生成
- `similarity_checker.py`
  - `difflib.SequenceMatcher`
- `article_pipeline.py`
  - ジョブ全体の進行管理

---

## 6. プロンプト管理の現在仕様

以前:

- `prompts/article_rewrite.yaml` を直接読む固定設計

現在:

- DBの `prompt_templates` テーブルを正本として使う
- 起動時、DBに `article_rewrite` がなければ YAML から初期投入
- ジョブ作成時に「その時点の有効テンプレート全文」を `article_jobs` にスナップショット保存
- 実行時はそのスナップショットを使う

### 保存されるスナップショット

`ArticleJob` に追加済み:

- `prompt_template_id`
- `prompt_version`
- `system_prompt_snapshot`
- `user_prompt_template_snapshot`

このため、後でプロンプトを更新しても過去ジョブの再現性は保てる。

### 使えるテンプレート変数

`app/schemas/prompt.py`

- `target_keyword`
- `original_article`
- `competitor_insights`
- `user_prompt`

注意:

- UIでは追加プロンプト入力を削除済みだが、テンプレート変数 `{{ user_prompt }}` 自体は残っている
- 現在のトップページからは `user_prompt` は送っていないので、実質 `"特になし"` が入る

---

## 7. DB初期化・簡易マイグレーション

`app/db/session.py`

実装済み:

- `Base.metadata.create_all()`
- `_ensure_article_jobs_columns()`
  - 既存SQLiteに `article_jobs` の追加カラムが無い場合 `ALTER TABLE` で足す
- `_seed_default_prompt_template()`
  - YAMLから最初の `PromptTemplate` を投入

制約:

- Alembic等は未導入
- 本格的なマイグレーション管理ではない
- SQLite前提の簡易対応

次のチャットで本格運用を進めるなら、将来的には Alembic 導入を検討してよい。

---

## 8. 設定と環境変数

### アプリ設定

`app/core/config.py`

主な値:

- `database_url`
- `openai_api_key`
- `openai_model`
- `search_provider`
- `google_search_api_key`
- `google_search_engine_id`
- `serpapi_api_key`
- `competitor_result_limit`
- `polling_interval_seconds`

### 現在の Render 設定

`render.yaml`

現在はモック前提:

```yaml
OPENAI_MODEL=mock
SEARCH_PROVIDER=mock
DATABASE_URL=sqlite:///./app.db
```

### 注意

- `config.py` のデフォルト `openai_model` は `gpt-4.1-mini`
- ただし `render.yaml` は `mock`
- `.env.example` も `gpt-4.1-mini` のまま

つまり現状は:

- ローカルの `.env` が無ければアプリ設定上は `gpt-4.1-mini`
- Renderは `mock`

この差は把握しておくこと。

---

## 9. モック運用の意味

### OpenAI mock

- `OPENAI_MODEL=mock`
- `app/services/article_generator.py`
- OpenAI APIは呼ばず、固定ロジックで記事を生成

### Search mock

- `SEARCH_PROVIDER=mock`
- `app/services/serp_search.py`
- 実検索APIを呼ばず、固定の上位3件を返す

### mock URL

- 元記事URLの例:
  - `https://example.com/mock/original`

競合も `example.com/mock/...` の固定HTMLを使う。

---

## 10. 主要ファイル

### まず読むべきファイル

- `app/main.py`
- `app/routes/pages.py`
- `app/routes/jobs.py`
- `app/db/models.py`
- `app/db/crud.py`
- `app/db/session.py`
- `app/services/article_pipeline.py`
- `app/services/prompt_builder.py`
- `app/services/article_generator.py`
- `app/services/serp_search.py`

### UIを見るなら

- `app/templates/base.html`
- `app/templates/index.html`
- `app/templates/result.html`
- `app/templates/prompts.html`
- `app/templates/guide.html`
- `app/static/css/app.css`

### プロンプト元データ

- `prompts/article_rewrite.yaml`

これは初期投入用としては今も意味がある。

---

## 11. 実行コマンド

### 初期セットアップ

```bash
make setup
```

### 通常起動

```bash
make run
```

### mock起動

```bash
make run-mock
```

### テスト

```bash
make test
make check
```

### mockジョブ送信

```bash
make mock-request
```

---

## 12. テスト状況

既存テスト:

- `tests/test_prompt_builder.py`
- `tests/test_seo_analyzer.py`
- `tests/test_similarity_checker.py`

直近で確認済み:

- `python3.11 -m compileall app`
- `.venv/bin/pytest`

現状のテストはユニット寄りで、HTTPルートやHTMX画面のE2Eテストは未整備。

---

## 13. 現在の既知のギャップ / 注意点

### 1. READMEが現状UIと完全一致していない

`README.md` は古い説明を一部含む可能性がある。

例:

- 追加プロンプト入力がある前提の文面が残っている可能性
- プロンプト管理 `/prompts` の説明が不足
- 画面構成の最新状態を十分反映していない

次チャットで整備候補。

### 2. `user_prompt` はバックエンドに残っている

- UIからは削除済み
- DBスキーマとテンプレート変数では残っている
- 互換性確保のため現時点では削っていない

次にやるなら:

- 本当に不要なら完全削除
- もしくは hidden/advanced 機能として残す

### 3. SQLite + Render Free は本番向きではない

- Render Free のローカルディスク永続性は弱い
- SQLiteは検証用途のまま

運用するなら:

- Postgres への移行
- マイグレーション管理導入

### 4. Prompt Editor は最小実装

できる:

- 編集
- 保存
- 複製
- 有効化

まだ無い:

- 差分表示
- 削除
- 下書き概念
- テスト実行ボタン
- バリデーションエラーのUI改善

### 5. 既存ジョブ詳細画面で runtime settings は毎回デフォルト値を表示

現在の `index()` / `get_job_result()` では、設定欄にジョブ実行時設定の再表示ではなく、アプリデフォルト値を入れている。

つまり:

- 過去ジョブを開いたとき、そのジョブで使った `search_provider` / `competitor_limit` / `openai_model` がフォームに復元されない

必要なら次の改善候補。

### 6. HTMLダウンロード時のCSSは簡素

`/jobs/{job_id}/download` は内蔵CSSで簡易整形しているだけ。

必要なら:

- ブランド用テンプレート
- 印刷向けCSS
- フルHTMLテンプレート化

---

## 14. 次チャットで依頼されそうな内容

可能性が高い順に列挙。

1. Renderデプロイまわりの最終調整
2. README更新
3. `.env.example` の整理
4. 実OpenAI / 実検索での確認
5. Prompt Editor の改善
6. DBをSQLiteから外部DBへ移行
7. `user_prompt` の完全削除
8. 結果画面のさらなる簡素化

---

## 15. 次チャットで最初に確認するとよいこと

次の Codex は、最初に以下を確認すると安全。

```bash
git status --short --branch
git log --oneline --decorate -n 10
make check
```

Render前提の確認なら:

```bash
sed -n '1,200p' render.yaml
sed -n '1,200p' .env.example
```

Prompt Editor に関わる作業なら:

```bash
sed -n '1,260p' app/routes/pages.py
sed -n '1,360p' app/routes/jobs.py
sed -n '1,260p' app/db/session.py
sed -n '1,260p' app/templates/prompts.html
```

---

## 16. 次の Codex への短い指示文

必要なら、次チャットの冒頭にこれをそのまま貼ればよい。

```text
このリポジトリは FastAPI + HTMX の記事生成アプリです。現在は main ブランチで clean、HEAD は 367e7bc40277b2c6dbe0a717710e25c58f2e5f23 です。トップページは入力フォームが上、結果が下の縦積みUIです。追加プロンプトUIは削除済みです。結果画面はHTMLプレビュー中心です。/prompts で DB保存のバージョン管理型プロンプト編集ができます。prompt_templates が正本で、job 作成時に prompt snapshot を保存します。Render は現在 mock 前提です。まず codex_next_chat_handoff.md を読んでから作業してください。
```

---

## 17. 最後に

この引き継ぎ書作成時点では、作業ツリーは clean です。  
次チャットでは、このファイルを起点に再開すれば現在地をほぼ再構築できます。
