
from fastapi import APIRouter

from app.schemas.chat import ChatRequest, GlobalChatRequest
from app.schemas.chat import ChatResponse, GlobalChatResponse
from app.services.chat.chat import chat_service
from app.services.chat.global_chat import global_chat_service


router = APIRouter(
    prefix="/v1/chat"
)


@router.post("/files", response_model=ChatResponse)
async def chat_files(chat_request: ChatRequest):
    """
    文件列表问答
    """
    return chat_service.chat(chat_request)


@router.post("/global", response_model=GlobalChatResponse)
async def chat_global(chat_request: GlobalChatRequest):
    """
    全局问答
    """
    return global_chat_service.chat(chat_request)
