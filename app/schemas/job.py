from pydantic import BaseModel, Field, HttpUrl, field_validator


class JobRuntimeSettings(BaseModel):
    search_provider: str = Field(default="mock")
    competitor_limit: int = Field(default=3, ge=1, le=5)
    openai_model: str = Field(default="gpt-4.1-mini", min_length=1, max_length=100)

    @field_validator("search_provider")
    @classmethod
    def validate_search_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"mock", "google", "serpapi"}:
            raise ValueError("検索プロバイダは mock / google / serpapi から選択してください。")
        return normalized

    @field_validator("openai_model")
    @classmethod
    def normalize_model(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("生成モデルを入力してください。")
        return cleaned


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
