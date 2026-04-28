import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.db.session import get_db
from app.schemas.job import JobCreateForm
from app.services.article_pipeline import run_article_job

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
templates.env.filters["from_json"] = lambda value: json.loads(value) if value else None


@router.post("", response_class=HTMLResponse)
def create_job(
    request: Request,
    background_tasks: BackgroundTasks,
    original_url: str = Form(...),
    target_keyword: str = Form(...),
    user_prompt: str = Form(default=""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        form = JobCreateForm(
            original_url=original_url,
            target_keyword=target_keyword,
            user_prompt=user_prompt,
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"]
        return templates.TemplateResponse(
            request=request,
            name="error_alert.html",
            context={
                "title": "入力内容を確認してください",
                "message": message,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if settings.requires_openai_key and not settings.openai_api_key:
        return templates.TemplateResponse(
            request=request,
            name="error_alert.html",
            context={
                "title": "OpenAI APIキーが必要です",
                "message": "`.env` に `OPENAI_API_KEY` を設定してください。ローカルデモのみであれば `OPENAI_MODEL=mock` でも動作します。",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    job = crud.create_article_job(
        db,
        original_url=str(form.original_url),
        target_keyword=form.target_keyword,
        user_prompt=form.user_prompt,
    )
    background_tasks.add_task(run_article_job, job.id)

    return templates.TemplateResponse(
        request=request,
        name="job_created.html",
        context={
            "job": job,
            "polling_interval_seconds": settings.polling_interval_seconds,
        },
    )


@router.get("/{job_id}", response_class=HTMLResponse)
def get_job(request: Request, job_id: str, db: Session = Depends(get_db)) -> HTMLResponse:
    job = crud.get_article_job_with_details(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ジョブが見つかりません。")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "job": job,
            "generated_article": job.generated_article,
            "polling_interval_seconds": settings.polling_interval_seconds,
        },
    )


@router.get("/{job_id}/status", response_class=HTMLResponse)
def get_job_status(request: Request, job_id: str, db: Session = Depends(get_db)) -> HTMLResponse:
    job = crud.get_article_job_with_details(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ジョブが見つかりません。")

    if job.status == "completed" and job.generated_article is not None:
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "job": job,
                "generated_article": job.generated_article,
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="job_status.html",
        context={
            "job": job,
            "polling_interval_seconds": settings.polling_interval_seconds,
        },
    )


@router.get("/{job_id}/result", response_class=HTMLResponse)
def get_job_result(request: Request, job_id: str, db: Session = Depends(get_db)) -> HTMLResponse:
    job = crud.get_article_job_with_details(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ジョブが見つかりません。")

    if job.status != "completed" or job.generated_article is None:
        return RedirectResponse(url=f"/jobs/{job_id}", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "job": job,
            "generated_article": job.generated_article,
            "polling_interval_seconds": settings.polling_interval_seconds,
        },
    )
