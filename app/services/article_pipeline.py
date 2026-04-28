from __future__ import annotations

import logging

import markdown

from app.db import crud
from app.db.session import SessionLocal
from app.schemas.article import CompetitorArticleData
from app.schemas.job import JobRuntimeSettings
from app.services.article_fetcher import fetch_html
from app.services.article_generator import generate_article
from app.services.content_extractor import extract_article_content
from app.services.prompt_builder import build_prompt
from app.services.seo_analyzer import analyze_articles
from app.services.serp_search import search_keyword
from app.services.similarity_checker import check_similarity

logger = logging.getLogger(__name__)


def run_article_job(job_id: str, runtime_settings: dict | None = None) -> None:
    db = SessionLocal()
    try:
        job = crud.get_article_job(db, job_id)
        if job is None:
            logger.error("Job not found: %s", job_id)
            return
        job_settings = JobRuntimeSettings.model_validate(runtime_settings or {})
        if not job.system_prompt_snapshot or not job.user_prompt_template_snapshot:
            raise RuntimeError("使用するプロンプトが保存されていません。")

        crud.update_job_status(db, job_id, "fetching_original")
        original_html = fetch_html(job.original_url)
        original_article = extract_article_content(job.original_url, original_html)

        crud.update_job_status(db, job_id, "searching")
        search_results = search_keyword(
            job.target_keyword,
            limit=job_settings.competitor_limit,
            provider=job_settings.search_provider,
        )

        crud.update_job_status(db, job_id, "fetching_competitors")
        competitor_articles: list[CompetitorArticleData] = []
        for result in search_results[: job_settings.competitor_limit]:
            try:
                competitor_html = fetch_html(result.url)
                extracted = extract_article_content(result.url, competitor_html)
                competitor_article = CompetitorArticleData(
                    rank=result.rank,
                    url=result.url,
                    title=extracted.title or result.title,
                    headings=extracted.headings,
                    summary=extracted.summary or result.snippet,
                    extracted_text=extracted.text,
                )
                competitor_articles.append(competitor_article)
                crud.create_competitor_article(
                    db,
                    job_id=job_id,
                    rank=competitor_article.rank,
                    url=competitor_article.url,
                    title=competitor_article.title,
                    headings=[item.model_dump() for item in competitor_article.headings],
                    summary=competitor_article.summary,
                    extracted_text=competitor_article.extracted_text,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to process competitor article %s: %s", result.url, exc)

        if not competitor_articles:
            raise RuntimeError("競合記事の取得に失敗しました。時間を置いて再試行してください。")

        crud.update_job_status(db, job_id, "analyzing")
        analysis = analyze_articles(original_article, competitor_articles)

        crud.update_job_status(db, job_id, "generating")
        prompt = build_prompt(
            original_article=original_article,
            target_keyword=job.target_keyword,
            user_prompt=job.user_prompt,
            analysis=analysis,
            system_template=job.system_prompt_snapshot,
            user_template=job.user_prompt_template_snapshot,
        )
        generated = generate_article(
            prompt=prompt,
            target_keyword=job.target_keyword,
            original_article=original_article,
            analysis=analysis,
            model_name=job_settings.openai_model,
        )

        crud.update_job_status(db, job_id, "checking")
        similarity_report = check_similarity(
            original_text=original_article.text,
            competitor_texts=[item.extracted_text for item in competitor_articles],
            generated_text=generated.article_markdown,
        )

        article_html = markdown.markdown(
            generated.article_markdown,
            extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
        )

        crud.create_generated_article(
            db,
            job_id=job_id,
            title=generated.title,
            meta_description=generated.meta_description,
            outline=[item.model_dump() for item in generated.outline],
            article_markdown=generated.article_markdown,
            article_html=article_html,
            faq=[item.model_dump() for item in generated.faq],
            copy_check=similarity_report.model_dump() | {"copy_avoidance_notes": generated.copy_avoidance_notes},
        )
        crud.update_job_status(db, job_id, "completed")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed", job_id)
        message = str(exc) or "記事生成中にエラーが発生しました。"
        crud.update_job_status(db, job_id, "failed", message)
    finally:
        db.close()
