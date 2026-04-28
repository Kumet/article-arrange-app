from app.schemas.article import (
    CompetitorInsight,
    ExtractedArticleData,
    HeadingItem,
    SeoAnalysis,
)
from app.services.prompt_builder import build_prompt


def test_prompt_builder_includes_keyword_and_competitor_insights() -> None:
    original = ExtractedArticleData(
        source_url="https://example.com/original",
        title="SEO記事改善の基本",
        headings=[
            HeadingItem(level=1, heading="SEO記事改善の基本"),
            HeadingItem(level=2, heading="改善前に確認したいこと"),
        ],
        text="本文です。検索意図と読者ニーズの整理が重要です。",
        summary="検索意図と読者ニーズの整理が重要です。",
    )
    analysis = SeoAnalysis(
        common_topics=["検索意図を分解する"],
        missing_topics=["比較表で整理する"],
        suggested_tables=["比較表で整理する比較表"],
        suggested_faqs=["比較表はどこまで必要ですか？"],
        competitor_insights=[
            CompetitorInsight(
                rank=1,
                title="競合ガイド",
                url="https://example.com/competitor",
                headings=["検索意図を分解する", "FAQの作り方"],
                missing_topics=["比較表で整理する"],
                summary="競合記事の要約です。",
            )
        ],
        notes=["競合本文は使わない"],
    )

    prompt = build_prompt(
        original_article=original,
        target_keyword="SEO 記事 リライト",
        user_prompt="専門家向けにしてください。",
        analysis=analysis,
        system_template="あなたは編集者です。",
        user_template="キーワード: {{ target_keyword }}\n元記事: {{ original_article }}\n競合: {{ competitor_insights }}\n追加: {{ user_prompt }}",
    )

    assert "SEO 記事 リライト" in prompt.user
    assert "競合ガイド" in prompt.user
    assert "比較表で整理する" in prompt.user
    assert "専門家向けにしてください。" in prompt.user
    assert "本文です。検索意図と読者ニーズの整理が重要です。" in prompt.user
    assert prompt.system == "あなたは編集者です。"
