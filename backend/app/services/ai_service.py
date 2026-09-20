"""Admin AI assistant orchestration.

The LLM only receives the sanitized output of ai_tools. It never receives a
database handle or raw SQL capability.
"""

import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import ai_tools


class AiConfigurationError(RuntimeError):
    pass


def chat(db: Session, message: str) -> tuple[str, dict]:
    if not settings.openai_api_key:
        raise AiConfigurationError("缺少 OPENAI_API_KEY，請在後端環境變量中配置")
    if not settings.openai_model:
        raise AiConfigurationError("缺少 OPENAI_MODEL，請在後端環境變量中配置")
    tool_context = ai_tools.build_tool_context(db, message)
    answer = _call_llm(message, tool_context)
    return answer, tool_context["tools"]


def _call_llm(message: str, tool_context: dict) -> str:
    base_url = settings.openai_base_url.rstrip("/")
    payload = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是校友商會小程序的超管數據助手。只能基於已提供的"
                    "tool_context 回答，不要聲稱已直接查詢數據庫。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"question": message, "tool_context": tool_context},
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.2,
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=payload,
        )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
