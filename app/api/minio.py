import mimetypes
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.libs.minio import MinioClient

router = APIRouter(
    prefix="/v1/minio"
)


@router.get("/{file_path:path}")
async def download_minio_file(file_path: str) -> StreamingResponse:
    """
    下载文件（通过 MinIO 路径）
    :param file_path: MinIO 中的文件路径（例如 "folder/subfolder/file.txt"）
    """
    file_stream, file_meta = await MinioClient().get_file(file_path)
    if file_meta["filename"].endswith(".gz"):
        content_type = "application/gzip"  # 或其他 MIME 类型，依据实际内容
    else:
        content_type = mimetypes.guess_type(file_meta["filename"])[0] or "application/octet-stream"
    # 为图片或其他可渲染文件，设置 Content-Disposition 为 inline
    content_disposition = "inline"  # 让浏览器直接渲染，而不是下载

    response = StreamingResponse(
        file_stream,
        media_type=content_type,
        headers={
            "Content-Disposition": f'{content_disposition}; filename="{file_meta["filename"]}"'
        }
    )

    # 将元数据附加到响应头，前端可以解析
    response.headers.update({
        "X-Filename": file_meta["filename"],
        "X-Content-Type": content_type,
        "X-Size": str(file_meta["size"])
    })

    return response
