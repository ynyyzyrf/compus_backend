from pydantic import BaseModel, Field


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AiChatResponse(BaseModel):
    answer: str
    tools: dict
