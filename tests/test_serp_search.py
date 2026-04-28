from app.schemas.job import JobRuntimeSettings
from app.services import serp_search


class _FakeDDGS:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def text(self, keyword: str, max_results: int = 3):
        return [
            {
                "title": f"{keyword} result 1",
                "href": "https://example.com/1",
                "body": "snippet 1",
            },
            {
                "title": f"{keyword} result 2",
                "href": "https://example.com/2",
                "body": "snippet 2",
            },
        ][:max_results]


def test_job_runtime_settings_accepts_ddgs() -> None:
    settings = JobRuntimeSettings(search_provider="ddgs")
    assert settings.search_provider == "ddgs"


def test_ddgs_search_returns_results(monkeypatch) -> None:
    monkeypatch.setitem(_fake_ddgs_module(), "DDGS", _FakeDDGS)
    results = serp_search._ddgs_search("python", 2)

    assert len(results) == 2
    assert results[0].url == "https://example.com/1"
    assert results[0].snippet == "snippet 1"


def _fake_ddgs_module() -> dict:
    import sys

    module = type(sys)("ddgs")
    sys.modules["ddgs"] = module
    return module.__dict__
