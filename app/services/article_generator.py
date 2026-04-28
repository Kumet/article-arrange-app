from __future__ import annotations

import json
import re

from app.core.config import get_settings
from app.schemas.article import (
    ExtractedArticleData,
    FaqItem,
    FixedReviewArticlePayload,
    GeneratedArticlePayload,
    HeadingItem,
    PromptMessages,
    ReviewSection,
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
    model_name: str | None = None,
) -> GeneratedArticlePayload:
    selected_model = (model_name or settings.openai_model).strip()

    if selected_model.lower() == "mock":
        return _build_mock_article(target_keyword, original_article, analysis)

    if not settings.openai_api_key:
        raise ArticleGenerationError("OpenAI APIキーが未設定です。.env を確認してください。")

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency issue
        raise ArticleGenerationError("OpenAI SDKが利用できません。依存関係を確認してください。") from exc

    client = OpenAI(api_key=settings.openai_api_key)

    try:
        response = client.responses.create(
            model=selected_model,
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
    if _is_fixed_review_payload(payload):
        return _sanitize_fixed_review_payload(payload)
    return _sanitize_legacy_payload(payload)


def _is_fixed_review_payload(payload: dict) -> bool:
    required_keys = {
        "product_name_line",
        "price_line",
        "item_number_line",
        "lead_paragraphs",
        "detail_section",
        "experience_section",
        "summary_section",
        "recommendation_rating",
    }
    return required_keys.issubset(payload.keys())


def _sanitize_fixed_review_payload(payload: dict) -> GeneratedArticlePayload:
    review_payload = FixedReviewArticlePayload(
        title=str(payload.get("title", "")).strip() or "商品レビュー",
        meta_description=str(payload.get("meta_description", "")).strip() or "元記事と検索上位記事を参考に再構成した商品レビューです。",
        product_name_line=_normalize_required_line(payload.get("product_name_line"), default="商品名：本文参照"),
        price_line=_normalize_required_line(payload.get("price_line"), default="購入価格：本文参照"),
        item_number_line=_normalize_required_line(payload.get("item_number_line"), default="ITEM# 本文参照"),
        lead_paragraphs=_normalize_paragraphs(payload.get("lead_paragraphs"), minimum=2),
        detail_section=_build_review_section(payload.get("detail_section"), default_heading="商品詳細", minimum=2),
        experience_section=_build_review_section(
            payload.get("experience_section"),
            default_heading="実際に試した感想",
            minimum=2,
        ),
        summary_section=_build_review_section(payload.get("summary_section"), default_heading="まとめ", minimum=1),
        recommendation_rating=int(payload.get("recommendation_rating", 3)),
        copy_avoidance_notes=_normalize_copy_notes(payload.get("copy_avoidance_notes")),
    )

    article_markdown = _render_fixed_review_markdown(review_payload)
    outline = [
        HeadingItem(level=2, heading=review_payload.detail_section.heading),
        HeadingItem(level=2, heading=review_payload.experience_section.heading),
        HeadingItem(level=2, heading=review_payload.summary_section.heading),
    ]

    return GeneratedArticlePayload(
        title=review_payload.title,
        meta_description=review_payload.meta_description,
        outline=outline,
        article_markdown=article_markdown,
        faq=[],
        copy_avoidance_notes=review_payload.copy_avoidance_notes,
    )


def _sanitize_legacy_payload(payload: dict) -> GeneratedArticlePayload:
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


def _normalize_required_line(value: object, *, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _normalize_paragraphs(value: object, *, minimum: int) -> list[str]:
    paragraphs = [str(item).strip() for item in (value or []) if str(item).strip()]
    if len(paragraphs) >= minimum:
        return paragraphs
    raise ValueError("paragraphs are required")


def _build_review_section(value: object, *, default_heading: str, minimum: int) -> ReviewSection:
    data = value if isinstance(value, dict) else {}
    heading = str(data.get("heading", "")).strip() or default_heading
    paragraphs = _normalize_paragraphs(data.get("paragraphs"), minimum=minimum)
    bullets = [str(item).strip() for item in data.get("bullets", []) if str(item).strip()]
    return ReviewSection(heading=heading, paragraphs=paragraphs, bullets=bullets)


def _normalize_copy_notes(value: object) -> list[str]:
    notes = [str(note).strip() for note in (value or []) if str(note).strip()]
    if notes:
        return notes
    return [
        "競合記事の本文は使わず、検索意図と不足観点だけを参考に再構成しました。",
        "参考フォーマットは型だけを取り入れ、文章表現は独自に書き直しています。",
    ]


def _render_fixed_review_markdown(payload: FixedReviewArticlePayload) -> str:
    sections = [
        ("lead", payload.lead_paragraphs, []),
        (payload.detail_section.heading, payload.detail_section.paragraphs, payload.detail_section.bullets),
        (payload.experience_section.heading, payload.experience_section.paragraphs, payload.experience_section.bullets),
        (payload.summary_section.heading, payload.summary_section.paragraphs, payload.summary_section.bullets),
    ]

    lines = [
        payload.product_name_line,
        payload.price_line,
        payload.item_number_line,
        "",
    ]

    for index, (heading, paragraphs, bullets) in enumerate(sections):
        if index > 0:
            lines.append(f"## {heading}")
            lines.append("")
        lines.extend(paragraphs)
        lines.append("")
        if bullets:
            lines.extend(f"- {bullet}" for bullet in bullets)
            lines.append("")

    lines.append(f"おすすめ度：{'★' * payload.recommendation_rating}")
    return "\n".join(lines).strip()


def _build_mock_article(
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> GeneratedArticlePayload:
    primary_missing = analysis.missing_topics[0] if analysis.missing_topics else "見落とされやすいポイント"
    review_payload = FixedReviewArticlePayload(
        title=f"{target_keyword}の気になるポイントを整理したレビュー",
        meta_description=f"{target_keyword}について、元記事の内容と検索上位3記事の傾向を踏まえながら、購入背景から使用感、総評まで個別レビュー型で再構成した記事です。",
        product_name_line=original_article.title or target_keyword,
        price_line="購入価格：本文参照",
        item_number_line="ITEM# 本文参照",
        lead_paragraphs=[
            f"{original_article.summary}",
            f"今回の記事では、{target_keyword}で読者が知りたい購入判断のポイントを先に押さえながら、元記事の情報をレビュー記事の流れに並べ替えています。",
            "検索上位3記事でよく触れられていた論点も確認しつつ、語り口や構成はそのまま真似せず、必要な観点だけを補いました。",
        ],
        detail_section=ReviewSection(
            heading="商品詳細",
            paragraphs=[
                "まずは元記事から読み取れる基本情報を整理し、購入前に見ておきたい条件を先にまとめます。",
                f"特に {primary_missing} の観点は比較時に見落とされやすいため、本文でも早めに触れて判断しやすくします。",
            ],
            bullets=[
                "元記事から確認できる仕様や特徴を先に明示する",
                "検索上位記事で頻出した観点を不足分だけ補う",
            ],
        ),
        experience_section=ReviewSection(
            heading="実際に試した感想",
            paragraphs=[
                "使用感や食べた印象のパートでは、元記事の事実を軸にしつつ、読者が気になりやすい良かった点と注意点を自然な流れで書き分けます。",
                "参考記事に寄せすぎないよう、表現は独自に書き換えながら、検索意図に直結する評価軸を明確にします。",
            ],
            bullets=[
                "最初の印象",
                "実際に良かった点",
                "気になる点や向いている人",
            ],
        ),
        summary_section=ReviewSection(
            heading="まとめ",
            paragraphs=[
                f"{target_keyword}で情報収集している読者に向けて、最後に向いている人や買う価値があるかを簡潔にまとめます。",
                "結論を短く締めることで、参考フォーマットの読み味に近づけつつ一覧ページ風にならないよう整えます。",
            ],
            bullets=[],
        ),
        recommendation_rating=4,
        copy_avoidance_notes=[
            "競合記事の本文は使わず、見出し傾向と不足トピックのみを反映しました。",
            "レビュー記事の型だけを借りて、文章の流れと表現は独自に再構成しました。",
        ],
    )
    return _sanitize_fixed_review_payload(review_payload.model_dump())


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
