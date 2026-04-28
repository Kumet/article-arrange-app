from pydantic import BaseModel, Field, HttpUrl, field_validator

FIXED_COMPETITOR_LIMIT = 3


class JobRuntimeSettings(BaseModel):
    search_provider: str = Field(default="mock")
    competitor_limit: int = Field(default=FIXED_COMPETITOR_LIMIT, ge=FIXED_COMPETITOR_LIMIT, le=FIXED_COMPETITOR_LIMIT)
    openai_model: str = Field(default="gpt-4.1-mini", min_length=1, max_length=100)

    @field_validator("search_provider")
    @classmethod
    def validate_search_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"mock", "ddgs", "google", "serpapi"}:
            raise ValueError("検索プロバイダは mock / ddgs / google / serpapi から選択してください。")
        return normalized

    @field_validator("openai_model")
    @classmethod
    def normalize_model(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("生成モデルを入力してください。")
        return cleaned

    @field_validator("competitor_limit")
    @classmethod
    def validate_competitor_limit(cls, value: int) -> int:
        if value != FIXED_COMPETITOR_LIMIT:
            raise ValueError(f"競合記事の取得件数は {FIXED_COMPETITOR_LIMIT} 件固定です。")
        return value


class JobCreateForm(BaseModel):
    original_url: HttpUrl
    target_keyword: str = Field(min_length=1, max_length=200)
    user_prompt: str = Field(default="", max_length=4000)

    @field_validator("target_keyword")
    @classmethod
    def validate_keyword(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("対策キーワードは必須です。")
        return cleaned

    @field_validator("user_prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        return value.strip()
