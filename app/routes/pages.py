import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.db.session import get_db
from app.schemas.job import JobRuntimeSettings
from app.schemas.prompt import ALLOWED_TEMPLATE_VARIABLES

router = APIRouter()
settings = get_settings()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
templates.env.filters["from_json"] = lambda value: json.loads(value) if value else None


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    job_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    job = crud.get_article_job_with_details(db, job_id) if job_id else None
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "job": job,
            "generated_article": job.generated_article if job else None,
            "polling_interval_seconds": settings.polling_interval_seconds,
            "runtime_settings": JobRuntimeSettings(
                search_provider="ddgs",
                competitor_limit=settings.competitor_result_limit,
                openai_model=settings.openai_model,
            ),
        },
    )


@router.get("/guide", response_class=HTMLResponse)
def guide(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="guide.html",
        context={},
    )


@router.get("/prompts", response_class=HTMLResponse)
def prompt_editor(
    request: Request,
    template_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    templates_list = crud.list_prompt_templates(db)
    active_template = crud.get_active_prompt_template(db)
    selected_template = crud.get_prompt_template(db, template_id) if template_id else active_template
    return templates.TemplateResponse(
        request=request,
        name="prompts.html",
        context={
            "templates_list": templates_list,
            "active_template": active_template,
            "selected_template": selected_template,
            "allowed_variables": sorted(ALLOWED_TEMPLATE_VARIABLES),
        },
    )
