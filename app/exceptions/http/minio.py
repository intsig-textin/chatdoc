from fastapi import HTTPException

_ERR_CODE_FILE_NOT_FOUND = 40100
_ERR_CODE_FILE_DOWNLOAD_ERROR = 40101


class _HTTPException(HTTPException):
    def __init__(self):
        super().__init__(self.status_code, self.detail)


class MinioFileNotFoundException(_HTTPException):

    status_code = 404

    detail = dict(
        code=_ERR_CODE_FILE_NOT_FOUND,
        message="Minio中文件未找到"
    )


class MinioFileDownloadErrorException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_FILE_DOWNLOAD_ERROR,
        message="Minio中文件下载失败"
    )
