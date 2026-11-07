from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question cannot be empty")
        return value


class SourceChunk(BaseModel):
    index: int
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str | None = None
    source_chunks: list[SourceChunk]