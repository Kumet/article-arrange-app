from pydantic import BaseModel, Field, HttpUrl, field_validator


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
