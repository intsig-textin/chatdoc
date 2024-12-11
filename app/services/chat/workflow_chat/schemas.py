
from typing import Union
from pydantic import BaseModel

from app.schemas.chat import ChatRequest, QuestionAnalysisSchema, RetrieveContextResponse
from app.schemas.doc import FileMetaSchema, DocTableRowSchema, DocParagraphSchema, DocOriginSchema, DocParagraphMetaTreeSchema


class Context(BaseModel):
    chat_request: ChatRequest                                   # Chat请求参数
    file_meta_list: list[FileMetaSchema] = []                   # 文件列表元数据
    question_analysis: QuestionAnalysisSchema = []              # 问题解析之后的结果
    table_retrieve_results: list[DocTableRowSchema] = []        # 表格检索结果
    paragraph_retrieve_results: list[DocParagraphSchema] = []   # 段落检索结果
    origin_slice_map: dict[str, DocOriginSchema] = []           # 源文件检索结果【DocOriginSchema.uuid: DocOriginSchema】
    paragraph_meta_tree_map: dict[str, DocParagraphMetaTreeSchema] = {}   # 段落uuid对应DocParagraphMeta的映射 【DocParagraphMetaTreeSchema.uuid, DocParagraphMetaTreeSchema】
    retrieve_contexts: list["RetrieveContext"] = []             # Rerank之后的召回列表
    retrieve_contexts_by_answer: list["RetrieveContext"] = []   # Rerank By Answer之后的召回列表
    llm_answer: str = ""                                        # llm的回答


class RetrieveContext(BaseModel):
    """
    召回上下文
    """
    retrieval_type: str                             # 召回类型 table|paragraph
    # 召回来源
    origin: Union[DocTableRowSchema, DocParagraphSchema, DocParagraphMetaTreeSchema] = None
    origin_slice: DocOriginSchema = None            # 源slice
    tree_slices: list[DocOriginSchema] = []         # slice的tree列表
    tree_text: str = ""                             # 片段用的text

    retrieve_rank_score: float = None               # 召回排序分数
    question_rerank_score: float = None             # 问题粗排分数
    repeat_score: float = None                      # 召回重复repeat分数
    rerank_score_before_llm: float = None           # 问答前融合分数
    answer_rerank_score: float = None               # 答案rerank分数
    # 送入大模型的text文本（有可能被token限制截断，为空时则取 get_text_str）

    @property
    def tree_slice_uuids(self):
        return [slice.uuid for slice in self.tree_slices]

    def __hash__(self):
        return hash(",".join(self.tree_slice_uuids))

    def intersect(self, other: "RetrieveContext") -> bool:
        """
        判断两个检索上下文是否重叠
        :param other:
        :return:
        """
        if self.origin_slice.file_uuid != other.origin_slice.file_uuid:
            return False

        if set(self.tree_slice_uuids).intersection(set(other.tree_slice_uuids)):
            return True

    def resp(self) -> RetrieveContextResponse:
        return RetrieveContextResponse(
            file_id=self.origin_slice.file_uuid,
            retrieval_type=self.retrieval_type,
            ori_ids=self.origin_slice.ori_ids,
            tree_text=self.tree_text
        )

    def get_answer_rerank_texts(self):
        return [
            tree_slice.content_md or tree_slice.content_html for tree_slice in self.tree_slices
        ]