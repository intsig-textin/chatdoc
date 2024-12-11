from fastapi import APIRouter
from fastapi import File, UploadFile

from app.exceptions.http.doc import ParseFileException, UnSupportedFileException
from app.schemas.doc import FileDeleteResponse, FileListResponse, FileParseResponse
from app.services.doc.parse import doc_parse_service_ins


router = APIRouter(
    prefix="/v1/doc"
)


@router.post("/parse", response_model=FileParseResponse)
async def parse_file(file: UploadFile = File(...)):
    """
    上传文件，返回文件元数据
    """
    if not doc_parse_service_ins.validate_file_type(file):
        raise UnSupportedFileException()

    file_meta = await doc_parse_service_ins.parse_file(file)
    if not file_meta:
        raise ParseFileException()

    return FileParseResponse(file_meta=file_meta)


@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(file_id: str):
    """
    删除文件，返回文件元数据
    """
    return await doc_parse_service_ins.delete_file(file_id)


# 文件列表接口
@router.get("/files", response_model=FileListResponse)
async def list_files():
    """
    获取所有已上传的文件元数据
    """
    file_list = await doc_parse_service_ins.get_all_files()
    return FileListResponse(files=file_list)
