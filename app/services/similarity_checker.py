from __future__ import annotations

from difflib import SequenceMatcher

from app.schemas.article import SimilarityReport


def check_similarity(
    *,
    original_text: str,
    competitor_texts: list[str],
    generated_text: str,
) -> SimilarityReport:
    original_similarity = _ratio(original_text, generated_text)
    competitor_similarities = [_ratio(text, generated_text) for text in competitor_texts if text.strip()]
    max_competitor_similarity = max(competitor_similarities, default=0.0)

    notes: list[str] = []
    shared_phrases = _shared_phrases([original_text, *competitor_texts], generated_text)
    if shared_phrases:
        notes.append(f"連続一致フレーズの候補があります: {', '.join(shared_phrases[:3])}")

    risk_level = _risk_level(original_similarity, max_competitor_similarity, bool(shared_phrases))
    notes.append(f"元記事との類似度: {original_similarity:.2f}")
    notes.append(f"競合記事との最大類似度: {max_competitor_similarity:.2f}")

    return SimilarityReport(
        original_similarity=round(original_similarity, 2),
        max_competitor_similarity=round(max_competitor_similarity, 2),
        risk_level=risk_level,
        notes=notes,
    )


def _ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _shared_phrases(source_texts: list[str], generated_text: str, window: int = 22) -> list[str]:
    normalized_generated = _normalize(generated_text)
    matches: list[str] = []
    seen: set[str] = set()

    for source in source_texts:
        normalized_source = _normalize(source)[:2000]
        for index in range(0, max(len(normalized_source) - window + 1, 0), 5):
            phrase = normalized_source[index : index + window].strip()
            if len(phrase) < window or phrase in seen:
                continue
            if phrase in normalized_generated:
                seen.add(phrase)
                matches.append(phrase)
            if len(matches) >= 5:
                return matches
    return matches


def _risk_level(
    original_similarity: float,
    competitor_similarity: float,
    has_shared_phrases: bool,
) -> str:
    if original_similarity >= 0.7 or competitor_similarity >= 0.6:
        return "high"
    if has_shared_phrases or original_similarity >= 0.45 or competitor_similarity >= 0.4:
        return "medium"
    return "low"
