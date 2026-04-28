import json

from sqlalchemy.orm import Session, joinedload

from app.db import models


def create_article_job(
    db: Session,
    *,
    original_url: str,
    target_keyword: str,
    user_prompt: str,
) -> models.ArticleJob:
    job = models.ArticleJob(
        original_url=original_url,
        target_keyword=target_keyword,
        user_prompt=user_prompt,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_article_job(db: Session, job_id: str) -> models.ArticleJob | None:
    return db.query(models.ArticleJob).filter(models.ArticleJob.id == job_id).first()


def get_article_job_with_details(db: Session, job_id: str) -> models.ArticleJob | None:
    return (
        db.query(models.ArticleJob)
        .options(
            joinedload(models.ArticleJob.competitor_articles),
            joinedload(models.ArticleJob.generated_article),
        )
        .filter(models.ArticleJob.id == job_id)
        .first()
    )


def update_job_status(
    db: Session,
    job_id: str,
    status: str,
    error_message: str | None = None,
) -> models.ArticleJob | None:
    job = get_article_job(db, job_id)
    if job is None:
        return None

    job.status = status
    job.error_message = error_message
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_competitor_article(
    db: Session,
    *,
    job_id: str,
    rank: int,
    url: str,
    title: str,
    headings: list[dict],
    summary: str,
    extracted_text: str,
) -> models.CompetitorArticle:
    competitor = models.CompetitorArticle(
        job_id=job_id,
        rank=rank,
        url=url,
        title=title,
        headings_json=json.dumps(headings, ensure_ascii=False),
        summary=summary,
        extracted_text=extracted_text,
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor


def create_generated_article(
    db: Session,
    *,
    job_id: str,
    title: str,
    meta_description: str,
    outline: list[dict],
    article_markdown: str,
    article_html: str,
    faq: list[dict],
    copy_check: dict,
) -> models.GeneratedArticle:
    existing = db.query(models.GeneratedArticle).filter(models.GeneratedArticle.job_id == job_id).first()
    if existing is not None:
        db.delete(existing)
        db.commit()

    generated_article = models.GeneratedArticle(
        job_id=job_id,
        title=title,
        meta_description=meta_description,
        outline_json=json.dumps(outline, ensure_ascii=False),
        article_markdown=article_markdown,
        article_html=article_html,
        faq_json=json.dumps(faq, ensure_ascii=False),
        copy_check_json=json.dumps(copy_check, ensure_ascii=False),
    )
    db.add(generated_article)
    db.commit()
    db.refresh(generated_article)
    return generated_article
