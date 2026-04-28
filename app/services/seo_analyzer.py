from __future__ import annotations

from collections import Counter

from app.schemas.article import CompetitorArticleData, CompetitorInsight, ExtractedArticleData, SeoAnalysis


def analyze_articles(
    original_article: ExtractedArticleData,
    competitor_articles: list[CompetitorArticleData],
) -> SeoAnalysis:
    original_topics = {_normalize(heading.heading) for heading in original_article.headings if heading.heading.strip()}
    competitor_headings = [
        heading.heading.strip()
        for competitor in competitor_articles
        for heading in competitor.headings
        if heading.level in {2, 3} and heading.heading.strip()
    ]

    heading_counter = Counter(_normalize(heading) for heading in competitor_headings)
    common_topics = [
        original
        for original in _unique_preserving_order(competitor_headings)
        if heading_counter[_normalize(original)] >= 2
    ][:5]

    missing_topics = [
        original
        for original in _unique_preserving_order(competitor_headings)
        if _normalize(original) not in original_topics
    ][:6]

    if not common_topics:
        common_topics = _unique_preserving_order(competitor_headings)[:4]

    suggested_tables = _build_suggested_tables(missing_topics, original_article.title)
    suggested_faqs = _build_suggested_faqs(missing_topics, original_article.title)

    competitor_insights = [
        CompetitorInsight(
            rank=competitor.rank,
            title=competitor.title,
            url=competitor.url,
            headings=[heading.heading for heading in competitor.headings if heading.level in {2, 3}],
            missing_topics=[
                heading.heading
                for heading in competitor.headings
                if heading.level in {2, 3} and _normalize(heading.heading) not in original_topics
            ][:4],
            summary=competitor.summary,
        )
        for competitor in competitor_articles
    ]

    notes = [
        "競合記事本文は直接プロンプトに渡さず、見出しと要約だけを使います。",
        "元記事に不足している見出しとFAQ候補を優先して補います。",
    ]
    if missing_topics:
        notes.append("不足トピックが見つかったため、構成の再設計を優先します。")

    return SeoAnalysis(
        common_topics=common_topics,
        missing_topics=missing_topics,
        suggested_tables=suggested_tables,
        suggested_faqs=suggested_faqs,
        competitor_insights=competitor_insights,
        notes=notes,
    )


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        normalized = _normalize(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(value)
    return unique_values


def _build_suggested_tables(missing_topics: list[str], article_title: str) -> list[str]:
    if missing_topics:
        primary_topic = missing_topics[0]
        return [
            f"{primary_topic}を整理する比較表",
            f"{article_title}で触れるべき要素のチェック表",
        ]
    return [f"{article_title}の改善ポイント整理表"]


def _build_suggested_faqs(missing_topics: list[str], article_title: str) -> list[str]:
    if not missing_topics:
        return [
            f"{article_title}を改善する優先順位は？",
            "比較表はどのタイミングで入れるべき？",
            "FAQは何問くらい必要？",
        ]

    return [
        f"{topic}はどこまで書けばよいですか？"
        for topic in missing_topics[:3]
    ]
