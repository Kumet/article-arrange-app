from pydantic import BaseModel, Field


class HeadingItem(BaseModel):
    level: int = Field(ge=1, le=6)
    heading: str = Field(min_length=1, max_length=500)


class ExtractedArticleData(BaseModel):
    source_url: str
    title: str
    headings: list[HeadingItem] = Field(default_factory=list)
    text: str
    summary: str


class SearchResultItem(BaseModel):
    rank: int
    title: str
    url: str
    snippet: str = ""


class CompetitorArticleData(BaseModel):
    rank: int
    url: str
    title: str
    headings: list[HeadingItem] = Field(default_factory=list)
    summary: str
    extracted_text: str


class CompetitorInsight(BaseModel):
    rank: int
    title: str
    url: str
    headings: list[str] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    summary: str = ""


class SeoAnalysis(BaseModel):
    common_topics: list[str] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    suggested_tables: list[str] = Field(default_factory=list)
    suggested_faqs: list[str] = Field(default_factory=list)
    competitor_insights: list[CompetitorInsight] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PromptMessages(BaseModel):
    system: str
    user: str


class FaqItem(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class GeneratedArticlePayload(BaseModel):
    title: str = Field(min_length=1)
    meta_description: str = Field(min_length=1)
    outline: list[HeadingItem] = Field(default_factory=list)
    article_markdown: str = Field(min_length=1)
    faq: list[FaqItem] = Field(default_factory=list)
    copy_avoidance_notes: list[str] = Field(default_factory=list)


class SimilarityReport(BaseModel):
    original_similarity: float = Field(ge=0, le=1)
    max_competitor_similarity: float = Field(ge=0, le=1)
    risk_level: str
    notes: list[str] = Field(default_factory=list)
