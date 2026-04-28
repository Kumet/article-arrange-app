import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import String

from app.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


class ArticleJob(Base):
    __tablename__ = "article_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    original_url = Column(String, nullable=False)
    target_keyword = Column(String, nullable=False)
    user_prompt = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="queued")
    error_message = Column(Text, nullable=True)
    prompt_template_id = Column(String, ForeignKey("prompt_templates.id"), nullable=True)
    prompt_version = Column(Integer, nullable=True)
    system_prompt_snapshot = Column(Text, nullable=False, default="")
    user_prompt_template_snapshot = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    competitor_articles = relationship(
        "CompetitorArticle",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CompetitorArticle.rank",
    )
    generated_article = relationship(
        "GeneratedArticle",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )
    prompt_template = relationship("PromptTemplate", back_populates="jobs")


class CompetitorArticle(Base):
    __tablename__ = "competitor_articles"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("article_jobs.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    headings_json = Column(Text, nullable=False, default="[]")
    summary = Column(Text, nullable=False, default="")
    extracted_text = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)

    job = relationship("ArticleJob", back_populates="competitor_articles")


class GeneratedArticle(Base):
    __tablename__ = "generated_articles"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("article_jobs.id"), nullable=False, unique=True)
    title = Column(String, nullable=False)
    meta_description = Column(Text, nullable=False)
    outline_json = Column(Text, nullable=False, default="[]")
    article_markdown = Column(Text, nullable=False)
    article_html = Column(Text, nullable=False)
    faq_json = Column(Text, nullable=False, default="[]")
    copy_check_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=utcnow)

    job = relationship("ArticleJob", back_populates="generated_article")


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    is_active = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    jobs = relationship("ArticleJob", back_populates="prompt_template")
