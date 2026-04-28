import json
from pathlib import Path
import re

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.db.session import get_db
from app.schemas.job import JobCreateForm, JobRuntimeSettings
from app.schemas.prompt import PromptTemplateForm
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
    search_provider: str = Form(default=""),
    competitor_limit: int = Form(default=3),
    openai_model: str = Form(default=""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        form = JobCreateForm(
            original_url=original_url,
            target_keyword=target_keyword,
            user_prompt=user_prompt,
        )
        runtime_settings = JobRuntimeSettings(
            search_provider=search_provider or settings.normalized_search_provider,
            competitor_limit=competitor_limit,
            openai_model=openai_model or settings.openai_model,
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

    if runtime_settings.openai_model.strip().lower() != "mock" and not settings.openai_api_key:
        return templates.TemplateResponse(
            request=request,
            name="error_alert.html",
            context={
                "title": "OpenAI APIキーが必要です",
                "message": "`.env` に `OPENAI_API_KEY` を設定してください。ローカルデモのみであれば `OPENAI_MODEL=mock` でも動作します。",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    active_prompt_template = crud.get_active_prompt_template(db)
    if active_prompt_template is None:
        return templates.TemplateResponse(
            request=request,
            name="error_alert.html",
            context={
                "title": "有効なプロンプトがありません",
                "message": "プロンプト管理画面で有効なテンプレートを作成または選択してください。",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    job = crud.create_article_job(
        db,
        original_url=str(form.original_url),
        target_keyword=form.target_keyword,
        user_prompt=form.user_prompt,
        prompt_template_id=active_prompt_template.id,
        prompt_version=active_prompt_template.version,
        system_prompt_snapshot=active_prompt_template.system_prompt,
        user_prompt_template_snapshot=active_prompt_template.user_prompt,
    )
    background_tasks.add_task(run_article_job, job.id, runtime_settings.model_dump())

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
            "runtime_settings": JobRuntimeSettings(
                search_provider=settings.normalized_search_provider,
                competitor_limit=settings.competitor_result_limit,
                openai_model=settings.openai_model,
            ),
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
            "runtime_settings": JobRuntimeSettings(
                search_provider=settings.normalized_search_provider,
                competitor_limit=settings.competitor_result_limit,
                openai_model=settings.openai_model,
            ),
        },
    )


@router.get("/{job_id}/download")
def download_job_result(job_id: str, db: Session = Depends(get_db)) -> Response:
    job = crud.get_article_job_with_details(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ジョブが見つかりません。")

    if job.status != "completed" or job.generated_article is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="生成結果がまだありません。")

    article = job.generated_article
    document = _build_download_html(title=article.title, body_html=article.article_html)
    filename = _build_download_filename(article.title)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return Response(content=document, media_type="text/html; charset=utf-8", headers=headers)


@router.post("/prompts")
def create_prompt_template_action(
    request: Request,
    system_prompt: str = Form(...),
    user_prompt: str = Form(...),
    is_active: str = Form(default="0"),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    form = PromptTemplateForm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        is_active=is_active == "1",
    )
    template = crud.create_prompt_template(
        db,
        name=form.name,
        system_prompt=form.system_prompt,
        user_prompt=form.user_prompt,
        is_active=form.is_active,
    )
    return RedirectResponse(url=f"/prompts?template_id={template.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/prompts/{template_id}")
def update_prompt_template_action(
    template_id: str,
    system_prompt: str = Form(...),
    user_prompt: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    form = PromptTemplateForm(system_prompt=system_prompt, user_prompt=user_prompt)
    updated = crud.update_prompt_template(
        db,
        template_id=template_id,
        system_prompt=form.system_prompt,
        user_prompt=form.user_prompt,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="プロンプトが見つかりません。")
    return RedirectResponse(url=f"/prompts?template_id={template_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/prompts/{template_id}/activate")
def activate_prompt_template_action(template_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    activated = crud.activate_prompt_template(db, template_id)
    if activated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="プロンプトが見つかりません。")
    return RedirectResponse(url=f"/prompts?template_id={template_id}", status_code=status.HTTP_303_SEE_OTHER)


def _build_download_html(*, title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <style>
      body {{
        margin: 0;
        background: #f8fafc;
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      main {{
        max-width: 960px;
        margin: 0 auto;
        padding: 48px 24px 80px;
      }}
      h1, h2, h3 {{ color: #0f172a; }}
      p, li {{ line-height: 1.8; }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin: 24px 0;
      }}
      th, td {{
        border: 1px solid #cbd5e1;
        padding: 12px;
        text-align: left;
      }}
      thead {{ background: #e2e8f0; }}
    </style>
  </head>
  <body>
    <main>
      <h1>{title}</h1>
      {body_html}
    </main>
  </body>
</html>
"""


def _build_download_filename(title: str) -> str:
    normalized = re.sub(r"\s+", "-", title.strip().lower())
    safe = re.sub(r"[^a-z0-9\-]+", "-", normalized).strip("-")
    return f"{safe or 'generated-article'}.html"
