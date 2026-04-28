from pydantic import BaseModel, Field, field_validator

ALLOWED_TEMPLATE_VARIABLES = {
    "target_keyword",
    "original_article",
    "competitor_insights",
    "user_prompt",
}


class PromptTemplateForm(BaseModel):
    name: str = Field(default="article_rewrite")
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    is_active: bool = False

    @field_validator("system_prompt", "user_prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("プロンプト本文は必須です。")
        return cleaned

    @field_validator("user_prompt")
    @classmethod
    def validate_template_variables(cls, value: str) -> str:
        import re

        variables = set(re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", value))
        unknown = sorted(variable for variable in variables if variable not in ALLOWED_TEMPLATE_VARIABLES)
        if unknown:
            raise ValueError(f"未対応のテンプレート変数があります: {', '.join(unknown)}")
        return value
