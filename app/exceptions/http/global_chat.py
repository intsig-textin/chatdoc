from fastapi import HTTPException

_ERR_CODE_NON_FILE_EXISTS = 30101
_ERR_CODE_QUESTION_ANALYSIS_FAIL = 30102
_ERR_CODE_LOCATE_QUERY_FILES_FAIL = 30103
_ERR_CODE_RETRIEVE_SMALL_GLOBAL_FAIL = 30104
_ERR_CODE_RETRIEVE_SMALL_FAIL = 30105
_ERR_CODE_RERANK_QUESTION_FAIL = 30106
_ERR_CODE_UPDATE_ORIGIN_SLICE_FAIL = 30107
_ERR_CODE_SMALL2BIG_FAIL = 30108
_ERR_CODE_TRUNCTION_FAIL = 30109
_ERR_CODE_GENERATE_FAIL = 30110
_ERR_CODE_RERANK_ANSWER_FAIL = 30111


class _HTTPException(HTTPException):
    def __init__(self):
        super().__init__(self.status_code, self.detail)


class NonFileExistsException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_NON_FILE_EXISTS,
        message="请先上传文件"
    )


class QuestionAnalysisException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_QUESTION_ANALYSIS_FAIL,
        message="问题解析失败"
    )


class LocateQueryFilesException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_LOCATE_QUERY_FILES_FAIL,
        message="问题解析失败"
    )


class RetrieveSmallGlobalException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_RETRIEVE_SMALL_GLOBAL_FAIL,
        message="全局召回片段失败"
    )


class RetrieveSmallException(_HTTPException):
    status_code = 500
    detail = dict(
        code=_ERR_CODE_RETRIEVE_SMALL_FAIL,
        message="文件召回片段失败"
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
