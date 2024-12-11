from fastapi import HTTPException

_ERR_CODE_PARSE_FILE_FAIL = 10100
_ERR_CODE_UN_SUPPORTED_FILE = 10101
_ERR_CODE_PDF2MD_FAIL = 10102
_ERR_CODE_CATALOG_FAIL = 10103
_ERR_CODE_GEN_ORG_SLICES_FAIL = 10104
_ERR_CODE_GEN_TABLE_SLICES_FAIL = 10105
_ERR_CODE_GEN_PARAGRAPH_SLICES_FAIL = 10106
_ERR_CODE_EMBEDDING_UOLOAD_SLICES_FAIL = 10107
_ERR_CODE_UPLOAD_FILE_INFO_FAIL = 10108
_ERR_CODE_UPLOAD2MINIO_INFO_FAIL = 10109


class _HTTPException(HTTPException):
    def __init__(self):
        super().__init__(self.status_code, self.detail)


class UnSupportedFileException(_HTTPException):

    status_code = 400

    detail = dict(
        code=_ERR_CODE_UN_SUPPORTED_FILE,
        message="文件格式不支持"
    )


class ParseFileException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_PARSE_FILE_FAIL,
        message="文件解析失败"
    )


class Pdf2MdException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_PDF2MD_FAIL,
        message="pdf2md解析失败"
    )


class CatalogException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_CATALOG_FAIL,
        message="catalog解析失败"
    )


class GenOriginSlicesException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_GEN_ORG_SLICES_FAIL,
        message="生成原始切片失败"
    )


class GenTableSlicesException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_GEN_TABLE_SLICES_FAIL,
        message="生成表格切片失败"
    )


class GenParagraphSlicesException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_GEN_PARAGRAPH_SLICES_FAIL,
        message="生成段落切片失败"
    )


class EmbeddingUploadSlicesException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_EMBEDDING_UOLOAD_SLICES_FAIL,
        message="切片Embedding/上传失败"
    )


class UploadFileInfoException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_UPLOAD_FILE_INFO_FAIL,
        message="上传文件信息失败"
    )


class UploadFile2MinioException(_HTTPException):

    status_code = 500

    detail = dict(
        code=_ERR_CODE_UPLOAD2MINIO_INFO_FAIL,
        message="上传MINIO失败"
    )
