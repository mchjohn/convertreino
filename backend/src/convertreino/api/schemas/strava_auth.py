from pydantic import BaseModel, Field, field_validator


class StravaTokenRequest(BaseModel):
    code: str = Field(..., min_length=1)

    @field_validator("code")
    @classmethod
    def strip_non_empty_code(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("code cannot be empty")
        return stripped
