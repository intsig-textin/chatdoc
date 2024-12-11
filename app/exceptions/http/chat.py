from config.config import settings
from fastapi import HTTPException

_ERR_CODE_EMPTY_FILE_IDS = 20101
_ERR_CODE_EXCEED_MAX_FILE_COUNT = 20102
_ERR_CODE_EXIST_INVALID_FILE_ID = 20103
_ERR_CODE_QUESTION_ANALYSIS_FAIL = 20104
_ERR_CODE_RETRIEVE_SMALL_FAIL = 20105
_ERR_CODE_UPDATE_ORIGIN_SLICE_FAIL = 20106
_ERR_CODE_RERANK_QUESTION_FAIL = 20107
_ERR_CODE_SMALL2BIG_FAIL = 20108
_ERR_CODE_TRUNCTION_FAIL = 20109
_ERR_CODE_GENERATE_FAIL = 20110
_ERR_CODE_RERANK_ANSWER_FAIL = 20111


class _HTTPException(HTTPException):
    def __init__(self):
        super().__init__(self.status_code, self.detail)


class EmptyFileIdsException(_HTTPException):

    status_code = 400

    detail = dict(
        code=_ERR_CODE_EMPTY_FILE_IDS,
        message="file_ids不能为空"
    )


class ExceedMaxFileCountException(_HTTPException):

    status_code = 400

    def __init__(self, limit_size=settings.app.chat_max_file_count):
        super().__init__()
        self.detail["message"] = f"最多上传{limit_size}个文件"

    detail = dict(
        code=_ERR_CODE_EXCEED_MAX_FILE_COUNT,
        message=f"最多上传{settings.app.chat_max_file_count}个文件"
    )


class InvalidFileIdException(_HTTPException):

    def __init__(self, file_ids):
        super().__init__()
        self.detail["message"] = f"存在无效的文件ID: {file_ids}"

    status_code = 400
    detail = dict(
        code=_ERR_CODE_EXIST_INVALID_FILE_ID,
        message="存在无效的文件ID"
    )


class QuestionAnalysisException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_QUESTION_ANALYSIS_FAIL,
        message="问题解析失败"
    )


class RetrieveSmallException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_RETRIEVE_SMALL_FAIL,
        message="召回片段失败"
    )


class UpdateOriginSliceException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_UPDATE_ORIGIN_SLICE_FAIL,
        message="更新元切片失败"
    )


class RerankQuestionException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_RERANK_QUESTION_FAIL,
        message="问题重排失败"
    )


class Small2BigException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_SMALL2BIG_FAIL,
        message="扩大切片失败"
    )


class TrunctionException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_TRUNCTION_FAIL,
        message="截断失败"
    )


class GenerationException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_GENERATE_FAIL,
        message="生成答案失败"
    )


class RerankAnswerException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_RERANK_ANSWER_FAIL,
        message="答案重排失败"
    )
