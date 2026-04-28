from textwrap import dedent

import httpx

from app.core.config import get_settings

settings = get_settings()


class ArticleFetchError(Exception):
    """Raised when a page cannot be fetched."""


MOCK_HTML_BY_URL = {
    "https://example.com/mock/original": dedent(
        """
        <html>
          <head><title>SEO記事改善の基本</title></head>
          <body>
            <article>
              <h1>SEO記事改善の基本</h1>
              <p>この記事では、既存記事を改善して検索意図に近づけるための考え方を解説します。</p>
              <h2>改善前に確認したいこと</h2>
              <p>読者像、検索意図、現在の構成を確認することが出発点です。</p>
              <h2>リライトで優先する要素</h2>
              <p>見出し、事例、FAQ、比較表を追加すると、理解しやすさが上がります。</p>
              <h3>検索意図の整理</h3>
              <p>指名検索か比較検討かで、必要な情報の深さが変わります。</p>
            </article>
          </body>
        </html>
        """
    ).strip(),
    "https://example.com/mock/competitor-overview": dedent(
        """
        <html>
          <head><title>SEO記事リライトの進め方ガイド</title></head>
          <body>
            <main>
              <h1>SEO記事リライトの進め方ガイド</h1>
              <h2>検索意図を分解する</h2>
              <p>顕在ニーズと潜在ニーズの両面から整理することが重要です。</p>
              <h2>競合構成の観察ポイント</h2>
              <p>FAQ、比較表、導入の切り口を見ます。</p>
              <h3>FAQの作り方</h3>
              <p>実務で出る質問を起点にします。</p>
            </main>
          </body>
        </html>
        """
    ).strip(),
    "https://example.com/mock/competitor-checklist": dedent(
        """
        <html>
          <head><title>検索上位に近づく記事改善チェックリスト</title></head>
          <body>
            <article>
              <h1>検索上位に近づく記事改善チェックリスト</h1>
              <h2>情報の抜け漏れ確認</h2>
              <p>比較軸、具体例、更新日などを点検します。</p>
              <h2>比較表で整理する</h2>
              <p>複数の選択肢や手順の違いを表で示すと理解しやすくなります。</p>
              <h3>読者が離脱しやすい要因</h3>
              <p>結論が遅い、次の行動が曖昧、FAQがない、などが代表例です。</p>
            </article>
          </body>
        </html>
        """
    ).strip(),
    "https://example.com/mock/competitor-case-study": dedent(
        """
        <html>
          <head><title>SEOリライトで成果を出す構成設計</title></head>
          <body>
            <article>
              <h1>SEOリライトで成果を出す構成設計</h1>
              <h2>読者フェーズ別に構成を変える</h2>
              <p>初心者向けと比較検討向けで、必要な章立ては変わります。</p>
              <h2>事例とFAQを追加する</h2>
              <p>体験談やFAQがあると、行動前の不安を解消しやすくなります。</p>
              <h3>公開後の改善ポイント</h3>
              <p>検索クエリのずれを見ながら、見出しの役割を再設計します。</p>
            </article>
          </body>
        </html>
        """
    ).strip(),
}


def fetch_html(url: str) -> str:
    if url in MOCK_HTML_BY_URL:
        return MOCK_HTML_BY_URL[url]

    headers = {"User-Agent": settings.user_agent}
    timeout = httpx.Timeout(settings.request_timeout_seconds)

    try:
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException as exc:
        raise ArticleFetchError("対象ページの取得がタイムアウトしました。時間を置いて再試行してください。") from exc
    except httpx.HTTPStatusError as exc:
        raise ArticleFetchError("対象ページの取得に失敗しました。URLが正しいか確認してください。") from exc
    except httpx.HTTPError as exc:
        raise ArticleFetchError("対象ページに接続できませんでした。URLまたはネットワーク状態を確認してください。") from exc
