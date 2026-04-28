import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.db.session import get_db

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
        },
    )
