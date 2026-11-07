from pydantic import BaseModel, Field, field_validator


class DocumentRequest(BaseModel):
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Document cannot be empty")
        return value


class DocumentResponse(BaseModel):
    document_id: str
    status: str
    text: str
