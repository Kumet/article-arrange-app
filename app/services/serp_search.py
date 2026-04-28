from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.schemas.article import SearchResultItem

settings = get_settings()


class SearchProviderError(Exception):
    """Raised when a search provider fails."""


def search_keyword(
    keyword: str,
    limit: int | None = None,
    provider: str | None = None,
) -> list[SearchResultItem]:
    result_limit = limit or settings.competitor_result_limit
    provider_name = (provider or settings.normalized_search_provider).strip().lower()

    if provider_name == "mock":
        return _mock_search_results(keyword, result_limit)
    if provider_name == "google":
        return _google_custom_search(keyword, result_limit)
    if provider_name == "serpapi":
        return _serpapi_search(keyword, result_limit)

    raise SearchProviderError(f"未対応の検索プロバイダです: {provider_name}")


def _mock_search_results(keyword: str, limit: int) -> list[SearchResultItem]:
    fixtures = [
        SearchResultItem(
            rank=1,
            title=f"{keyword}の検索意図を整理するリライトガイド",
            url="https://example.com/mock/competitor-overview",
            snippet=f"{keyword}で上位を狙うための検索意図とFAQの考え方をまとめた記事です。",
        ),
        SearchResultItem(
            rank=2,
            title=f"{keyword}の改善チェックリスト",
            url="https://example.com/mock/competitor-checklist",
            snippet=f"{keyword}に必要な比較表と見出し点検の観点を整理した記事です。",
        ),
        SearchResultItem(
            rank=3,
            title=f"{keyword}の構成設計と事例",
            url="https://example.com/mock/competitor-case-study",
            snippet=f"{keyword}向けに事例と読者フェーズ別の構成をまとめた記事です。",
        ),
    ]
    return fixtures[:limit]


def _google_custom_search(keyword: str, limit: int) -> list[SearchResultItem]:
    if not settings.google_search_api_key or not settings.google_search_engine_id:
        raise SearchProviderError("Google Custom Search APIの設定が不足しています。")

    params = {
        "key": settings.google_search_api_key,
        "cx": settings.google_search_engine_id,
        "q": keyword,
        "num": limit,
    }
    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            response = client.get("https://www.googleapis.com/customsearch/v1", params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SearchProviderError("Google検索APIの呼び出しに失敗しました。") from exc

    payload = response.json()
    items = payload.get("items", [])
    if not items:
        raise SearchProviderError("Google検索APIから結果を取得できませんでした。")

    return [
        SearchResultItem(
            rank=index,
            title=item.get("title", "タイトル未取得"),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
        )
        for index, item in enumerate(items[:limit], start=1)
        if item.get("link")
    ]


def _serpapi_search(keyword: str, limit: int) -> list[SearchResultItem]:
    if not settings.serpapi_api_key:
        raise SearchProviderError("SerpAPIの設定が不足しています。")

    params = {
        "engine": "google",
        "q": keyword,
        "num": limit,
        "api_key": settings.serpapi_api_key,
    }
    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            response = client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SearchProviderError("SerpAPIの呼び出しに失敗しました。") from exc

    payload = response.json()
    items = payload.get("organic_results", [])
    if not items:
        raise SearchProviderError("SerpAPIから結果を取得できませんでした。")

    return [
        SearchResultItem(
            rank=index,
            title=item.get("title", "タイトル未取得"),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
        )
        for index, item in enumerate(items[:limit], start=1)
        if item.get("link")
    ]
