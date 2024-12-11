from typing import Generator, Optional, Union
import json
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel


class StreamContentSchema(BaseModel):
    delta: str = ""


class StreamFinishSchema(BaseModel):
    content: str = ""
    total_token: int = 0


class RetrieveContextResponse(BaseModel):
    """
    RetrieveContext 中的Meta信息
    """
    retrieval_type: str = ""        # 召回类型 table|paragraph
    # 召回来源
    file_id: str = ""               # 文件id
    ori_ids: list[str] = []         # 召回溯源位置信息
    tree_text: str = ""             # 召回文本


class StreamRetrieveContextResponse(BaseModel):
    retrieval: list[RetrieveContextResponse]


ChatStreamGenerator = Generator[Union[StreamContentSchema, StreamFinishSchema, StreamRetrieveContextResponse, dict], None, None]


class ChatRequest(BaseModel):
    file_ids: list[str]
    question: str
    stream: bool = False


class GlobalChatRequest(BaseModel):
    question: str
    stream: bool = False


class ChatResponse(BaseModel):
    # 用于普通非流式返回
    content: Optional[str] = None
    total_tokens: int = 0
    retrieval: list[RetrieveContextResponse] = []

    # 流式返回时的类型
    stream_content: Optional[ChatStreamGenerator] = None

    class Config:
        arbitrary_types_allowed = True  # 允许 Generator 类型

    @ classmethod
    def create_stream_response(cls, stream_content: ChatStreamGenerator) -> StreamingResponse:

        def _process(stream_iter: Generator):
            for obj in stream_iter:
                yield json.dumps(obj, ensure_ascii=False)
        return EventSourceResponse(_process(stream_content))


class GlobalChatResponse(ChatResponse):
    ...


class QuestionAnalysisSchema(BaseModel):
    rewrite_question: str
    keywords: list[str] = []
    years: list[str] = []


class EmbeddingArgSchema(BaseModel):
    field: str
    size: int = 10
    dimension: int = 1024
