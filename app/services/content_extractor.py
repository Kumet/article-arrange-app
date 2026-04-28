from __future__ import annotations

from bs4 import BeautifulSoup
import trafilatura

from app.schemas.article import ExtractedArticleData, HeadingItem


class ContentExtractionError(Exception):
    """Raised when article content cannot be extracted."""


def extract_article_content(source_url: str, html: str) -> ExtractedArticleData:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    headings = _extract_headings(soup)
    main_text = _extract_with_trafilatura(html) or _extract_with_bs4(soup)

    if not main_text.strip():
        raise ContentExtractionError("本文の抽出に失敗しました。別のURLで試してください。")

    summary = _build_summary(main_text)
    return ExtractedArticleData(
        source_url=source_url,
        title=title,
        headings=headings,
        text=main_text.strip(),
        summary=summary,
    )


def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    return "タイトル未取得"


def _extract_headings(soup: BeautifulSoup) -> list[HeadingItem]:
    headings: list[HeadingItem] = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        headings.append(HeadingItem(level=int(tag.name[-1]), heading=text))
    return headings


def _extract_with_trafilatura(html: str) -> str:
    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    return (extracted or "").strip()


def _extract_with_bs4(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    root = soup.find("article") or soup.find("main") or soup.body or soup
    chunks: list[str] = []
    for tag in root.find_all(["p", "li"]):
        text = tag.get_text(" ", strip=True)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _build_summary(text: str, limit: int = 260) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
