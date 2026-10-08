"""AI 扩展预留模块。

第一期不启用任何模型调用，仅预留：
1. LLMService 抽象接口 —— 后续实现 GLM/DeepSeek/通义等接入
2. /api/v1/ai/chat 接口骨架 —— ChatBI 对话式查询
3. 本模块依赖 inventory_transaction 完整流水数据，为需求预测提供数据基础
"""
from abc import ABC, abstractmethod

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models import SysUser

router = APIRouter(prefix="/ai", tags=["AI 助手"])


class LLMService(ABC):
    """大模型服务抽象：后续按需实现具体厂商接入。"""

    @abstractmethod
    async def chat(self, messages: list[dict], context: dict | None = None) -> str:
        """messages: [{"role": "user"|"assistant"|"system", "content": str}]"""


class MockLLMService(LLMService):
    """占位实现：第一期返回固定提示。"""

    async def chat(self, messages: list[dict], context: dict | None = None) -> str:
        return "AI 助手即将上线。当前版本已预留对话接口与流水数据基础。"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


_service: LLMService = MockLLMService()


def get_llm_service() -> LLMService:
    return _service


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current: SysUser = Depends(get_current_user),
    llm: LLMService = Depends(get_llm_service),
):
    """ChatBI 骨架：后续在此注入用户数据权限上下文 + NL2SQL/工具调用。"""
    reply = await llm.chat([{"role": "user", "content": body.message}])
    return ChatResponse(reply=reply)
