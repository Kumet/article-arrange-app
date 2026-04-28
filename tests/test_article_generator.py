from app.services.article_generator import _parse_generation_output
from app.schemas.article import ExtractedArticleData, HeadingItem, SeoAnalysis


def test_parse_generation_output_builds_fixed_review_markdown() -> None:
    generated = _parse_generation_output(
        raw_text="""
        {
          "title": "テスト商品レビュー",
          "meta_description": "これは固定レビュー形式のテスト用メタディスクリプションです。100文字前後に収める想定で作成しています。",
          "product_name_line": "テスト商品 500g",
          "price_line": "購入価格：998円（2026年4月）",
          "item_number_line": "ITEM# 12345",
          "lead_paragraphs": ["導入1です。", "導入2です。", "導入3です。"],
          "detail_section": {
            "heading": "商品詳細",
            "paragraphs": ["詳細1です。", "詳細2です。"],
            "bullets": ["仕様A", "仕様B"]
          },
          "experience_section": {
            "heading": "実際に試した感想",
            "paragraphs": ["感想1です。", "感想2です。"],
            "bullets": ["良かった点", "気になった点"]
          },
          "summary_section": {
            "heading": "まとめ",
            "paragraphs": ["まとめ1です。"],
            "bullets": []
          },
          "recommendation_rating": 4,
          "copy_avoidance_notes": ["構成だけ参考にして文章は独自化しました。"]
        }
        """,
        target_keyword="テスト商品",
        original_article=_build_original_article(),
        analysis=SeoAnalysis(),
    )

    assert generated.title == "テスト商品レビュー"
    assert generated.faq == []
    assert generated.outline[0].heading == "商品詳細"
    assert "テスト商品 500g" in generated.article_markdown
    assert "## 実際に試した感想" in generated.article_markdown
    assert "- 良かった点" in generated.article_markdown
    assert "おすすめ度：★★★★" in generated.article_markdown


def test_parse_generation_output_accepts_legacy_payload() -> None:
    generated = _parse_generation_output(
        raw_text="""
        {
          "title": "旧形式の記事",
          "meta_description": "旧形式のテストです。",
          "outline": [{"level": 2, "heading": "見出し"}],
          "article_markdown": "## 見出し\\n\\n本文です。",
          "faq": [{"question": "質問", "answer": "回答"}],
          "copy_avoidance_notes": ["旧形式でも処理できます。"]
        }
        """,
        target_keyword="テスト商品",
        original_article=_build_original_article(),
        analysis=SeoAnalysis(),
    )

    assert generated.title == "旧形式の記事"
    assert generated.faq[0].question == "質問"
    assert generated.article_markdown == "## 見出し\n\n本文です。"


def _build_original_article() -> ExtractedArticleData:
    return ExtractedArticleData(
        source_url="https://example.com/original",
        title="元記事タイトル",
        headings=[HeadingItem(level=1, heading="元記事タイトル")],
        text="元記事本文です。",
        summary="元記事要約です。",
    )
