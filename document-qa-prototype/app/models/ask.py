from pydantic import BaseModel, Field, field_validator, model_validator


class AskRequest(BaseModel):
    document_id: str | None = None
    use_context: bool = True
    question: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_document_id(self):
        if self.use_context and (self.document_id is None or not self.document_id.strip()):
            raise ValueError("document_id is required when using document context")
        return self

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


class LLMMetadata(BaseModel):
    invoked: bool = False
    provider: str | None = None
    requested_model: str | None = None
    actual_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: float | None = None
    cost_usd: float | None = None


class RetrievalMetadata(BaseModel):
    embedding_provider: str | None = None
    embedding_model: str | None = None
    retrieval_duration_ms: float | None = None


class AskResponse(BaseModel):
    answer: str | None = None
    source_chunks: list[SourceChunk]
    llm: LLMMetadata | None = None
    use_context: bool = True
    retrieval: RetrievalMetadata | None = None