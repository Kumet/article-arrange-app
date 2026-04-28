from collections.abc import Generator

from pathlib import Path

import yaml
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_article_jobs_columns()
    _seed_default_prompt_template()


def _ensure_article_jobs_columns() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("article_jobs")}
    required_columns = {
        "prompt_template_id": "ALTER TABLE article_jobs ADD COLUMN prompt_template_id VARCHAR",
        "prompt_version": "ALTER TABLE article_jobs ADD COLUMN prompt_version INTEGER",
        "system_prompt_snapshot": "ALTER TABLE article_jobs ADD COLUMN system_prompt_snapshot TEXT NOT NULL DEFAULT ''",
        "user_prompt_template_snapshot": "ALTER TABLE article_jobs ADD COLUMN user_prompt_template_snapshot TEXT NOT NULL DEFAULT ''",
    }
    with engine.begin() as connection:
        for column_name, statement in required_columns.items():
            if column_name not in columns:
                connection.execute(text(statement))


def _seed_default_prompt_template() -> None:
    from app.db.models import PromptTemplate

    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "article_rewrite.yaml"
    with SessionLocal() as session:
        existing = session.query(PromptTemplate).filter(PromptTemplate.name == "article_rewrite").first()
        if existing is not None:
            return

        with prompt_path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file)

        template = PromptTemplate(
            name="article_rewrite",
            version=1,
            system_prompt=payload.get("system", "").strip(),
            user_prompt=payload.get("user", "").strip(),
            is_active=1,
        )
        session.add(template)
        session.commit()
