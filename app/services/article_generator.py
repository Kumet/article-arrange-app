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
    ReviewTable,
    SeoAnalysis,
)

settings = get_settings()
MIN_ARTICLE_CHARACTERS = 3000


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
            return _sanitize_payload(
                payload,
                target_keyword=target_keyword,
                original_article=original_article,
                analysis=analysis,
            )
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


def _sanitize_payload(
    payload: dict,
    *,
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> GeneratedArticlePayload:
    if _is_fixed_review_payload(payload):
        return _sanitize_fixed_review_payload(
            payload,
            target_keyword=target_keyword,
            original_article=original_article,
            analysis=analysis,
        )
    return _sanitize_legacy_payload(payload)


def _is_fixed_review_payload(payload: dict) -> bool:
    required_keys = {
        "product_name_line",
        "price_line",
        "item_number_line",
        "lead_paragraphs",
        "overview_section",
        "detail_section",
        "experience_section",
        "selection_section",
        "caution_section",
        "summary_section",
        "comparison_table",
        "recommendation_rating",
    }
    return required_keys.issubset(payload.keys())


def _sanitize_fixed_review_payload(
    payload: dict,
    *,
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> GeneratedArticlePayload:
    heading_keyword = _heading_keyword(target_keyword)
    review_payload = FixedReviewArticlePayload(
        title=str(payload.get("title", "")).strip() or "商品レビュー",
        meta_description=str(payload.get("meta_description", "")).strip() or "元記事と検索上位記事を参考に再構成した商品レビューです。",
        product_name_line=_normalize_required_line(payload.get("product_name_line"), default="商品名：本文参照"),
        price_line=_normalize_required_line(payload.get("price_line"), default="購入価格：本文参照"),
        item_number_line=_normalize_required_line(payload.get("item_number_line"), default="ITEM# 本文参照"),
        lead_paragraphs=_normalize_paragraphs(payload.get("lead_paragraphs"), minimum=2),
        overview_section=_build_review_section(
            payload.get("overview_section"),
            default_heading=f"{heading_keyword}とは",
            minimum=2,
        ),
        detail_section=_build_review_section(payload.get("detail_section"), default_heading="商品詳細", minimum=2),
        experience_section=_build_review_section(
            payload.get("experience_section"),
            default_heading="実際に試した感想",
            minimum=2,
        ),
        selection_section=_build_review_section(
            payload.get("selection_section"),
            default_heading=f"{heading_keyword}の選び方",
            minimum=2,
        ),
        caution_section=_build_review_section(
            payload.get("caution_section"),
            default_heading=f"{heading_keyword}の注意点",
            minimum=2,
        ),
        summary_section=_build_review_section(payload.get("summary_section"), default_heading="まとめ", minimum=1),
        comparison_table=_build_review_table(payload.get("comparison_table"), target_keyword=target_keyword, analysis=analysis),
        recommendation_rating=int(payload.get("recommendation_rating", 3)),
        copy_avoidance_notes=_normalize_copy_notes(payload.get("copy_avoidance_notes")),
    )

    review_payload = _enforce_review_requirements(
        review_payload,
        target_keyword=target_keyword,
        original_article=original_article,
        analysis=analysis,
    )
    article_markdown = _render_fixed_review_markdown(review_payload)
    outline = [HeadingItem(level=2, heading=section.heading) for section in _ordered_sections(review_payload)]

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


def _build_review_table(value: object, *, target_keyword: str, analysis: SeoAnalysis) -> ReviewTable:
    data = value if isinstance(value, dict) else {}
    headers = [str(item).strip() for item in data.get("headers", []) if str(item).strip()]
    rows = [
        [str(cell).strip() for cell in row if str(cell).strip()]
        for row in data.get("rows", [])
        if isinstance(row, (list, tuple))
    ]
    rows = [row for row in rows if len(row) >= 2]
    if len(headers) < 2:
        headers = ["確認項目", "見るポイント", "判断のコツ"]
    if not rows:
        primary_topic = analysis.missing_topics[0] if analysis.missing_topics else f"{target_keyword}の注目ポイント"
        secondary_topic = analysis.common_topics[0] if analysis.common_topics else "使いやすさ"
        rows = [
            [primary_topic, "元記事で触れている要素を整理する", "比較前に条件をそろえる"],
            [secondary_topic, "口コミで注目されやすい点を確認する", "自分の使い方に合うか判断する"],
            [f"{target_keyword}の注意点", "購入前に見落としやすい点を確認する", "先に気になる点をつぶしておく"],
        ]
    caption = str(data.get("caption", "")).strip() or f"{_heading_keyword(target_keyword)}を整理する比較表"
    normalized_rows = [row[: len(headers)] + [""] * max(0, len(headers) - len(row)) for row in rows]
    return ReviewTable(caption=caption, headers=headers, rows=normalized_rows)


def _normalize_copy_notes(value: object) -> list[str]:
    notes = [str(note).strip() for note in (value or []) if str(note).strip()]
    if notes:
        return notes
    return [
        "競合記事の本文は使わず、検索意図と不足観点だけを参考に再構成しました。",
        "参考フォーマットは型だけを取り入れ、文章表現は独自に書き直しています。",
    ]


def _heading_keyword(target_keyword: str) -> str:
    compact = re.sub(r"[\s\u3000]+", "", target_keyword).strip()
    return compact or "レビュー記事"


def _ordered_sections(payload: FixedReviewArticlePayload) -> list[ReviewSection]:
    return [
        payload.overview_section,
        payload.detail_section,
        payload.experience_section,
        payload.selection_section,
        payload.caution_section,
        payload.summary_section,
    ]


def _enforce_review_requirements(
    payload: FixedReviewArticlePayload,
    *,
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> FixedReviewArticlePayload:
    heading_keyword = _heading_keyword(target_keyword)
    normalized_sections: list[ReviewSection] = []
    default_suffixes = [
        "とは",
        "の商品詳細",
        "を試した感想",
        "の選び方",
        "の注意点",
        "まとめ",
    ]

    for section, suffix in zip(_ordered_sections(payload), default_suffixes):
        heading = _normalize_heading(section.heading, heading_keyword=heading_keyword, fallback_suffix=suffix)
        normalized_sections.append(
            ReviewSection(
                heading=heading,
                paragraphs=[_normalize_sentence_spacing(paragraph) for paragraph in section.paragraphs],
                bullets=[_normalize_sentence_spacing(bullet) for bullet in section.bullets if bullet.strip()],
            )
        )

    payload.overview_section = normalized_sections[0]
    payload.detail_section = normalized_sections[1]
    payload.experience_section = normalized_sections[2]
    payload.selection_section = normalized_sections[3]
    payload.caution_section = normalized_sections[4]
    payload.summary_section = normalized_sections[5]

    if not any(section.bullets for section in normalized_sections):
        payload.selection_section.bullets = _default_selection_bullets(heading_keyword, analysis)

    if not payload.comparison_table.rows:
        payload.comparison_table = _build_review_table({}, target_keyword=target_keyword, analysis=analysis)

    _expand_payload_to_minimum_length(
        payload,
        target_keyword=target_keyword,
        original_article=original_article,
        analysis=analysis,
        minimum_characters=MIN_ARTICLE_CHARACTERS,
    )
    return payload


def _normalize_heading(heading: str, *, heading_keyword: str, fallback_suffix: str) -> str:
    compact_heading = re.sub(r"[\s\u3000]+", "", heading).strip("：:-|｜")
    compact_heading = compact_heading.replace("　", "")
    if not compact_heading:
        return f"{heading_keyword}{fallback_suffix}"
    if heading_keyword in compact_heading:
        return compact_heading
    if compact_heading.startswith("の") or compact_heading.startswith("を"):
        return f"{heading_keyword}{compact_heading}"
    if compact_heading in {"商品詳細", "実際に試した感想", "まとめ"}:
        suffix_map = {
            "商品詳細": "の商品詳細",
            "実際に試した感想": "を試した感想",
            "まとめ": "まとめ",
        }
        return f"{heading_keyword}{suffix_map[compact_heading]}"
    return f"{heading_keyword}の{compact_heading}"


def _normalize_sentence_spacing(text: str) -> str:
    return re.sub(r"[ \t\u3000]+", "", text).strip()


def _default_selection_bullets(heading_keyword: str, analysis: SeoAnalysis) -> list[str]:
    bullets = [
        f"{heading_keyword}で優先したい条件を先に決める",
        f"{heading_keyword}の比較で外せないポイントをそろえる",
    ]
    if analysis.missing_topics:
        bullets.append(f"{_normalize_sentence_spacing(analysis.missing_topics[0])}まで確認して判断する")
    return bullets


def _expand_payload_to_minimum_length(
    payload: FixedReviewArticlePayload,
    *,
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
    minimum_characters: int,
) -> None:
    expansion_blocks = _build_expansion_blocks(
        target_keyword=target_keyword,
        original_article=original_article,
        analysis=analysis,
    )
    sections = _ordered_sections(payload)
    block_index = 0
    while _rendered_character_count(payload) < minimum_characters and block_index < len(expansion_blocks):
        section = sections[block_index % len(sections)]
        section.paragraphs.append(expansion_blocks[block_index])
        block_index += 1

    while _rendered_character_count(payload) < minimum_characters:
        for section in sections:
            section.paragraphs.append(
                _normalize_sentence_spacing(
                    f"{_heading_keyword(target_keyword)}については、元記事で触れている内容をそのまま繰り返すのではなく、"
                    "比較前に確認したい条件、実際に使う場面で役立つ視点、購入後に後悔しないための考え方を順番に整理しておくと、"
                    "読者が自分に合うかどうかを判断しやすくなります。"
                )
            )
            if _rendered_character_count(payload) >= minimum_characters:
                break


def _build_expansion_blocks(
    *,
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> list[str]:
    heading_keyword = _heading_keyword(target_keyword)
    missing_topics = analysis.missing_topics[:4] or [f"{heading_keyword}の注目ポイント", f"{heading_keyword}の比較軸"]
    common_topics = analysis.common_topics[:3] or [f"{heading_keyword}の使いやすさ", f"{heading_keyword}の満足度"]
    competitor_titles = "、".join(item.title for item in analysis.competitor_insights[:3] if item.title) or "上位記事"
    summary_excerpt = original_article.summary or original_article.text[:220]

    blocks = [
        f"{heading_keyword}を調べている人は、価格だけでなく、どんな場面で満足しやすいかまで知りたいことが多いです。"
        f"そのため導入では{summary_excerpt}という元記事の軸を残しつつ、購入前に迷いやすいポイントを先回りして整理しておくと、"
        "記事全体の読みやすさが大きく上がります。",
        f"今回の{heading_keyword}では、検索上位でよく見かけた{common_topics[0]}や{common_topics[-1]}といった観点も意識しながら、"
        "単なる感想で終わらせず、選ぶ理由と見送る理由の両方を示す流れにすると、比較検討中の読者にとって実用的な内容になります。",
        f"特に{missing_topics[0]}は元記事だけでは伝わりにくいことがあるため、具体的な使用場面や比較ポイントに言い換えて補足すると、"
        f"{heading_keyword}の理解が深まりやすくなります。上位記事を見ても、この部分が明確だと最後まで読まれやすい傾向がありました。",
        f"{heading_keyword}の商品詳細パートでは、数字や仕様を並べるだけではなく、それがどのようなメリットにつながるのかを一文ずつ補足するのが有効です。"
        "読者はスペックそのものより、自分の使い方に置き換えたときの意味を知りたいので、特徴と実感をセットで書くと理解しやすくなります。",
        f"実際に試した感想では、第一印象だけでなく、使い始めてから気づいた良さや気になる点まで触れることで、{heading_keyword}の評価に厚みが出ます。"
        "良い点だけに寄せず、どんな人に向くかまで言い切ると、レビュー記事としての信頼感が高まります。",
        f"{heading_keyword}の選び方を説明するパートでは、{missing_topics[-1]}のような見落とされやすい項目を先に出すと、"
        "読者が比較軸をそろえやすくなります。価格、使いやすさ、満足度のように大きな軸を先に置き、その後で細かい違いを見る流れが自然です。",
        f"注意点のパートでは、{competitor_titles}のような上位記事で共通して触れられていた観点を参考にしつつ、"
        "本文ではコピーせずに自分の言葉で整理し直すことが重要です。注意点を率直に書くことで、結論の説得力も強まります。",
        f"まとめでは、{heading_keyword}が向いている人と慎重に考えたい人を分けて示すと、読者が行動しやすくなります。"
        "最後に判断材料を短く整理しておくと、長文でも結論を見失いにくくなります。",
    ]
    return [_normalize_sentence_spacing(block) for block in blocks]


def _rendered_character_count(payload: FixedReviewArticlePayload) -> int:
    markdown = _render_fixed_review_markdown(payload)
    plain_text = re.sub(r"[#|\-\n]", "", markdown)
    return len(plain_text)


def _render_fixed_review_markdown(payload: FixedReviewArticlePayload) -> str:
    lines = [
        payload.product_name_line,
        payload.price_line,
        payload.item_number_line,
        "",
    ]

    lines.extend(payload.lead_paragraphs)
    lines.append("")

    for section in _ordered_sections(payload):
        lines.append(f"## {section.heading}")
        lines.append("")
        lines.extend(section.paragraphs)
        lines.append("")
        if section == payload.detail_section:
            lines.extend(_render_table_markdown(payload.comparison_table))
            lines.append("")
        if section.bullets:
            lines.extend(f"- {bullet}" for bullet in section.bullets)
            lines.append("")

    lines.append(f"おすすめ度：{'★' * payload.recommendation_rating}")
    return "\n".join(lines).strip()


def _render_table_markdown(table: ReviewTable) -> list[str]:
    header_line = "| " + " | ".join(table.headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(table.headers)) + " |"
    row_lines = []
    for row in table.rows:
        normalized_row = list(row[: len(table.headers)]) + [""] * max(0, len(table.headers) - len(row))
        row_lines.append("| " + " | ".join(normalized_row[: len(table.headers)]) + " |")
    return [f"**{table.caption}**", "", header_line, separator_line, *row_lines]


def _build_mock_article(
    target_keyword: str,
    original_article: ExtractedArticleData,
    analysis: SeoAnalysis,
) -> GeneratedArticlePayload:
    heading_keyword = _heading_keyword(target_keyword)
    primary_missing = analysis.missing_topics[0] if analysis.missing_topics else "見落とされやすいポイント"
    review_payload = FixedReviewArticlePayload(
        title=f"{heading_keyword}の気になるポイントを整理したレビュー",
        meta_description=f"{heading_keyword}について、元記事の内容と検索上位3記事の傾向を踏まえながら、購入背景から使用感、総評まで個別レビュー型で再構成した記事です。",
        product_name_line=original_article.title or target_keyword,
        price_line="購入価格：本文参照",
        item_number_line="ITEM# 本文参照",
        lead_paragraphs=[
            f"{original_article.summary}",
            f"今回の記事では、{heading_keyword}で読者が知りたい購入判断のポイントを先に押さえながら、元記事の情報をレビュー記事の流れに並べ替えています。",
            "検索上位3記事でよく触れられていた論点も確認しつつ、語り口や構成はそのまま真似せず、必要な観点だけを補いました。",
        ],
        overview_section=ReviewSection(
            heading=f"{heading_keyword}とは",
            paragraphs=[
                f"{heading_keyword}を検討するときは、まずどんな魅力があり、どんな人に向いているかを短時間で把握できる構成が重要です。",
                "導入で結論を急ぎすぎず、購入背景や第一印象を含めて読み始めやすい流れを作ると、比較中の読者にも伝わりやすくなります。",
            ],
            bullets=[
                f"{heading_keyword}で先に確認したい条件を整理する",
                f"{heading_keyword}を選ぶ理由と迷う理由を両方出す",
            ],
        ),
        detail_section=ReviewSection(
            heading=f"{heading_keyword}の商品詳細",
            paragraphs=[
                "まずは元記事から読み取れる基本情報を整理し、購入前に見ておきたい条件を先にまとめます。",
                f"特に {primary_missing} の観点は比較時に見落とされやすいため、本文でも早めに触れて判断しやすくします。",
            ],
            bullets=[],
        ),
        experience_section=ReviewSection(
            heading=f"{heading_keyword}を試した感想",
            paragraphs=[
                "使用感や食べた印象のパートでは、元記事の事実を軸にしつつ、読者が気になりやすい良かった点と注意点を自然な流れで書き分けます。",
                "参考記事に寄せすぎないよう、表現は独自に書き換えながら、検索意図に直結する評価軸を明確にします。",
            ],
            bullets=[],
        ),
        selection_section=ReviewSection(
            heading=f"{heading_keyword}の選び方",
            paragraphs=[
                f"{heading_keyword}を比較するときは、価格、使いやすさ、満足度のような大きな軸を先にそろえると判断しやすくなります。",
                "そのうえで自分の用途に合うか、継続して使いやすいかを確認すると、後悔の少ない選び方につながります。",
            ],
            bullets=[
                "価格だけでなく用途との相性も確認する",
                "上位記事で頻出した比較軸を先に整理する",
            ],
        ),
        caution_section=ReviewSection(
            heading=f"{heading_keyword}の注意点",
            paragraphs=[
                "良い点だけを見て判断すると、購入後にギャップを感じることがあります。",
                "気になる点や向いていないケースも先に把握しておくことで、レビュー記事としての信頼感が高まります。",
            ],
            bullets=[
                "気になる点を先に確認してから比較する",
                "自分の使い方に合うかを最後に見直す",
            ],
        ),
        summary_section=ReviewSection(
            heading=f"{heading_keyword}まとめ",
            paragraphs=[
                f"{heading_keyword}で情報収集している読者に向けて、最後に向いている人や買う価値があるかを簡潔にまとめます。",
                "結論を短く締めることで、参考フォーマットの読み味に近づけつつ一覧ページ風にならないよう整えます。",
            ],
            bullets=[],
        ),
        comparison_table=ReviewTable(
            caption=f"{heading_keyword}を整理する比較表",
            headers=["確認項目", "見たいポイント", "判断のコツ"],
            rows=[
                ["購入前の条件", "何を優先したいか", "用途を先に決める"],
                ["使いやすさ", "続けやすい特徴があるか", "実際の利用場面で考える"],
                ["注意点", "気になる点を許容できるか", "デメリットも先に把握する"],
            ],
        ),
        recommendation_rating=4,
        copy_avoidance_notes=[
            "競合記事の本文は使わず、見出し傾向と不足トピックのみを反映しました。",
            "レビュー記事の型だけを借りて、文章の流れと表現は独自に再構成しました。",
        ],
    )
    return _sanitize_fixed_review_payload(
        review_payload.model_dump(),
        target_keyword=target_keyword,
        original_article=original_article,
        analysis=analysis,
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
