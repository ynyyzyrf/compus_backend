from fastapi import APIRouter, HTTPException, status

from app.core.deps import DbSession, SuperAdmin
from app.schemas.ai import AiChatRequest, AiChatResponse
from app.services import ai_service

router = APIRouter(prefix="/admin/ai", tags=["admin/ai"])


@router.post("/chat", response_model=AiChatResponse)
def chat(payload: AiChatRequest, _: SuperAdmin, db: DbSession) -> AiChatResponse:
    try:
        answer, tools = ai_service.chat(db, payload.message)
    except ai_service.AiConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    return AiChatResponse(answer=answer, tools=tools)
