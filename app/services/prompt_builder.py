from __future__ import annotations

from pathlib import Path

import yaml

from app.schemas.article import ExtractedArticleData, PromptMessages, SeoAnalysis

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "article_rewrite.yaml"


def build_prompt(
    *,
    original_article: ExtractedArticleData,
    target_keyword: str,
    user_prompt: str,
    analysis: SeoAnalysis,
) -> PromptMessages:
    payload = _load_prompt_template()

    original_article_text = _format_original_article(original_article)
    competitor_insights_text = _format_competitor_insights(analysis)

    replacements = {
        "target_keyword": target_keyword,
        "original_article": original_article_text,
        "competitor_insights": competitor_insights_text,
        "user_prompt": user_prompt or "特になし",
    }

    system_prompt = payload["system"].strip()
    user_prompt_text = _fill_template(payload["user"], replacements).strip()
    return PromptMessages(system=system_prompt, user=user_prompt_text)


def _load_prompt_template() -> dict[str, str]:
    with PROMPT_PATH.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file)
    return {
        "system": payload.get("system", ""),
        "user": payload.get("user", ""),
    }


def _format_original_article(article: ExtractedArticleData) -> str:
    headings = "\n".join(f"- h{item.level}: {item.heading}" for item in article.headings[:12]) or "- 見出し未取得"
    excerpt = article.text[:3000]
    return (
        f"タイトル: {article.title}\n"
        f"URL: {article.source_url}\n"
        f"要約: {article.summary}\n"
        f"見出し:\n{headings}\n\n"
        f"本文抜粋:\n{excerpt}"
    )


def _format_competitor_insights(analysis: SeoAnalysis) -> str:
    sections: list[str] = []
    if analysis.common_topics:
        sections.append("共通トピック:\n" + "\n".join(f"- {topic}" for topic in analysis.common_topics))
    if analysis.missing_topics:
        sections.append("元記事に不足している観点:\n" + "\n".join(f"- {topic}" for topic in analysis.missing_topics))
    if analysis.suggested_tables:
        sections.append("追加すべき表:\n" + "\n".join(f"- {topic}" for topic in analysis.suggested_tables))
    if analysis.suggested_faqs:
        sections.append("FAQ候補:\n" + "\n".join(f"- {topic}" for topic in analysis.suggested_faqs))

    competitor_blocks = []
    for insight in analysis.competitor_insights:
        headings = "\n".join(f"  - {heading}" for heading in insight.headings[:8]) or "  - 取得なし"
        missing = "\n".join(f"  - {topic}" for topic in insight.missing_topics[:4]) or "  - 特になし"
        competitor_blocks.append(
            "\n".join(
                [
                    f"順位: {insight.rank}",
                    f"タイトル: {insight.title}",
                    f"URL: {insight.url}",
                    f"見出し:",
                    headings,
                    f"要約: {insight.summary}",
                    f"不足観点:",
                    missing,
                ]
            )
        )

    if competitor_blocks:
        sections.append("競合記事インサイト:\n" + "\n\n".join(competitor_blocks))

    if analysis.notes:
        sections.append("分析メモ:\n" + "\n".join(f"- {note}" for note in analysis.notes))

    return "\n\n".join(sections)


def _fill_template(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
    return rendered
