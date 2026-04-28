from app.schemas.article import CompetitorArticleData, ExtractedArticleData, HeadingItem
from app.services.seo_analyzer import analyze_articles


def test_seo_analyzer_extracts_missing_topics_and_common_topics() -> None:
    original = ExtractedArticleData(
        source_url="https://example.com/original",
        title="SEO記事改善の基本",
        headings=[
            HeadingItem(level=1, heading="SEO記事改善の基本"),
            HeadingItem(level=2, heading="改善前に確認したいこと"),
            HeadingItem(level=2, heading="リライトで優先する要素"),
        ],
        text="既存記事の構成を見直すための基本を説明する。",
        summary="既存記事の構成を見直すための基本を説明する。",
    )
    competitors = [
        CompetitorArticleData(
            rank=1,
            url="https://example.com/1",
            title="競合1",
            headings=[
                HeadingItem(level=2, heading="検索意図を分解する"),
                HeadingItem(level=2, heading="比較表で整理する"),
            ],
            summary="summary 1",
            extracted_text="text 1",
        ),
        CompetitorArticleData(
            rank=2,
            url="https://example.com/2",
            title="競合2",
            headings=[
                HeadingItem(level=2, heading="検索意図を分解する"),
                HeadingItem(level=3, heading="FAQの作り方"),
            ],
            summary="summary 2",
            extracted_text="text 2",
        ),
    ]

    result = analyze_articles(original, competitors)

    assert "検索意図を分解する" in result.common_topics
    assert "比較表で整理する" in result.missing_topics
    assert result.suggested_tables
    assert len(result.suggested_faqs) >= 1
