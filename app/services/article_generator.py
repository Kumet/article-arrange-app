from __future__ import annotations

import json
import re

from openai import OpenAI

from app.core.config import get_settings
from app.schemas.article import (
    ExtractedArticleData,
    FaqItem,
    GeneratedArticlePayload,
    HeadingItem,
    PromptMessages,
    SeoAnalysis,
)

settings = get_settings()


class ArticleGenerationError(Exception):
    """Raised when article generation fails."""


def generate_article(
    *,
    prompt: PromptMessages,
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> GeneratedArticlePayload:
    if settings.openai_model.strip().lower() == "mock":
        return _build_mock_article(target_keyword, original_article, analysis)

    if not settings.openai_api_key:
        raise ArticleGenerationError("OpenAI APIキーが未設定です。.env を確認してください。")

    client = OpenAI(api_key=settings.openai_api_key)

    try:
        response = client.responses.create(
            model=settings.openai_model,
            instructions=prompt.system,
            input=prompt.user,
        )
    except Exception as exc:  # noqa: BLE001
        raise ArticleGenerationError("OpenAI APIで記事生成に失敗しました。時間を置いて再試行してください。") from exc

    raw_text = (getattr(response, "output_text", "") or "").strip()
    if not raw_text:
        raise ArticleGenerationError("OpenAI APIから有効な出力を受け取れませんでした。")

    return _parse_generation_output(
        raw_text=raw_text,
        target_keyword=target_keyword,
        original_article=original_article,
        analysis=analysis,
    )


def _parse_generation_output(
    *,
    raw_text: str,
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> GeneratedArticlePayload:
    candidates = [raw_text, _strip_code_fence(raw_text), _extract_json_block(raw_text)]

    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
            return _sanitize_payload(payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    fallback = _build_mock_article(target_keyword, original_article, analysis)
    fallback.article_markdown = raw_text
    fallback.copy_avoidance_notes.insert(0, "JSONパースに失敗したため、本文はモデル出力をそのまま保存しました。")
    return fallback


def _strip_code_fence(raw_text: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE).strip()


def _extract_json_block(raw_text: str) -> str:
    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    return match.group(0).strip() if match else ""


def _sanitize_payload(payload: dict) -> GeneratedArticlePayload:
    outline = [
        HeadingItem(
            level=int(item.get("level", 2)),
            heading=str(item.get("heading", "")).strip(),
        )
        for item in payload.get("outline", [])
        if str(item.get("heading", "")).strip()
    ]
    faq = [
        FaqItem(
            question=str(item.get("question", "")).strip(),
            answer=str(item.get("answer", "")).strip(),
        )
        for item in payload.get("faq", [])
        if str(item.get("question", "")).strip() and str(item.get("answer", "")).strip()
    ]
    copy_notes = [str(note).strip() for note in payload.get("copy_avoidance_notes", []) if str(note).strip()]

    if not faq:
        faq = _default_faq("記事")
    if not outline:
        outline = [HeadingItem(level=2, heading="記事のポイント")]
    if not copy_notes:
        copy_notes = ["競合記事の本文を使わず、要点だけを参考に再構成しました。"]

    article_markdown = str(payload.get("article_markdown", "")).strip()
    if not article_markdown:
        raise ValueError("article_markdown is required")

    title = str(payload.get("title", "")).strip() or "生成記事"
    meta_description = str(payload.get("meta_description", "")).strip() or "検索意図を踏まえて再構成した記事です。"

    return GeneratedArticlePayload(
        title=title,
        meta_description=meta_description,
        outline=outline,
        article_markdown=article_markdown,
        faq=faq,
        copy_avoidance_notes=copy_notes,
    )


def _build_mock_article(
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> GeneratedArticlePayload:
    primary_missing = analysis.missing_topics[0] if analysis.missing_topics else "不足トピック"
    table_title = analysis.suggested_tables[0] if analysis.suggested_tables else f"{target_keyword}の整理表"
    faq = _default_faq(target_keyword)
    outline = [
        HeadingItem(level=2, heading=f"{target_keyword}で押さえる前提"),
        HeadingItem(level=2, heading=f"{target_keyword}で不足しやすい観点"),
        HeadingItem(level=3, heading=primary_missing),
        HeadingItem(level=2, heading=f"{target_keyword}の改善手順"),
        HeadingItem(level=2, heading="よくある質問"),
    ]

    article_markdown = f"""## {target_keyword}で押さえる前提

{original_article.summary}

- 読者の検索意図を最初に整理する
- 元記事にない視点を明確に補う
- 競合記事は構成の参考としてのみ使う

## {target_keyword}で不足しやすい観点

競合記事の見出し傾向を見ると、特に **{primary_missing}** の観点が不足しやすい状態でした。ここを補うことで、単なる言い換えではなく情報価値を追加できます。

### {primary_missing}

不足していた論点を独立した小見出しとして扱い、読者が次に知りたい内容へ自然につながるよう再構成します。

## {target_keyword}の改善手順

| 項目 | 何を確認するか | 追加するとよい要素 |
| --- | --- | --- |
| 検索意図 | 顕在ニーズと潜在ニーズの差 | 導入の結論、比較ポイント |
| 構成 | 見出しの抜け漏れ | {table_title} |
| 説得力 | 実務での判断材料があるか | 事例、FAQ、チェックリスト |

1. 元記事の主張を残しつつ、読者が比較したい観点を先に出します。
2. 競合で頻出した見出しを分解し、そのまま模倣せず不足トピックだけ補います。
3. FAQと比較表を追加して、検索意図ごとの不安を減らします。

## よくある質問

### {faq[0].question}
{faq[0].answer}

### {faq[1].question}
{faq[1].answer}

### {faq[2].question}
{faq[2].answer}
"""

    return GeneratedArticlePayload(
        title=f"{target_keyword}を踏まえて再設計する記事改善ガイド",
        meta_description=f"{target_keyword}で必要な検索意図と不足トピックを整理し、比較表とFAQを含めて記事を再構成するための実践ガイドです。",
        outline=outline,
        article_markdown=article_markdown,
        faq=faq,
        copy_avoidance_notes=[
            "競合記事の本文は使わず、見出し傾向と不足トピックのみを反映しました。",
            "元記事の要点を保持しながら、情報の順番と切り口を再設計しました。",
            "比較表とFAQを追加し、単純な言い換えではない情報価値を加えました。",
        ],
    )


def _default_faq(target_keyword: str) -> list[FaqItem]:
    return [
        FaqItem(
            question=f"{target_keyword}の記事改善は何から始めるべきですか？",
            answer="まず検索意図の確認と、既存見出しに不足している観点の洗い出しから始めると整理しやすくなります。",
        ),
        FaqItem(
            question="比較表は必ず必要ですか？",
            answer="比較検討や手順説明を含む記事では、要点を短時間で理解してもらうために比較表が有効です。",
        ),
        FaqItem(
            question="FAQはいくつ入れるべきですか？",
            answer="最低3問を目安に、読者が行動前に迷いやすい点を優先して入れるのが実務的です。",
        ),
    ]
