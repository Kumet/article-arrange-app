from app.services.similarity_checker import check_similarity


def test_similarity_checker_returns_low_risk_for_distinct_content() -> None:
    report = check_similarity(
        original_text="既存記事では検索意図の整理と見出し改善を説明する。",
        competitor_texts=[
            "競合記事では事例とFAQの追加について触れている。",
            "別の記事では比較表の見せ方を紹介している。",
        ],
        generated_text="新しい記事では読者フェーズに応じた構成設計と比較表の使い分けを中心に解説する。",
    )

    assert report.risk_level == "low"
    assert report.original_similarity < 0.7
    assert report.max_competitor_similarity < 0.6


def test_similarity_checker_detects_high_similarity() -> None:
    source = "検索意図を確認してFAQを追加し、比較表で違いを整理します。"
    report = check_similarity(
        original_text=source,
        competitor_texts=["競合記事でも検索意図を確認してFAQを追加する構成を採用している。"],
        generated_text=source,
    )

    assert report.risk_level in {"medium", "high"}
    assert report.original_similarity >= 0.7
