from fastapi import APIRouter
from app.api.chat import router as chat_router
from app.api.doc import router as doc_router
from app.api.minio import router as minio_router

api_router = APIRouter()

api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(doc_router, tags=["doc"])
api_router.include_router(minio_router, tags=["minio"])
