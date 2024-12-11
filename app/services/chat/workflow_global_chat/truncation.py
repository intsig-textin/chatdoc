
import logging
import traceback
from app.exceptions.http.global_chat import TrunctionException
from app.schemas.doc import DocParagraphMetaTreeSchema, DocTableRowSchema, DocOriginSchema
from app.services.chat.workflow_global_chat.schemas import Context, RetrieveContext
from app.support.helper import duplicates_list, group_by_func, log_duration
from config.config import settings


@log_duration()
def truncation(context: Context) -> list[RetrieveContext]:
    try:
        # 生成tree_text属性
        for retrieve_context in context.retrieve_contexts:
            retrieve_context.tree_text = generate_tree_text(retrieve_context, context.origin_slice_map, context.paragraph_meta_tree_map)
        # 最多取前20个文件
        retrieve_contexts = []
        for file_contexts in [x[1] for x in group_by_func(context.retrieve_contexts, lambda x: x.origin_slice.file_uuid)][20:]:
            retrieve_contexts.extend(file_contexts)

        # topP
        retrieve_contexts = top_p(context.retrieve_contexts, top_p_score=settings.app.wf_global_chat.rough_rank_score)
        # topN
        if len(retrieve_contexts) > settings.app.wf_global_chat.retrieve_top_n:
            retrieve_contexts = retrieve_contexts[:settings.app.wf_global_chat.retrieve_top_n]
        # token limit
        if len(context.final_files) == 1:
            retrieve_contexts = truncation_by_token_limit(retrieve_contexts, max_length=settings.app.wf_global_chat.retrieval_max_length / 2)
        else:
            retrieve_contexts = truncation_by_token_limit(retrieve_contexts, max_length=settings.app.wf_global_chat.retrieval_max_length)

        return retrieve_contexts

    except Exception as e:
        logging.error(f'truncation error: {e}, {traceback.format_exc()}')
        raise TrunctionException()


def generate_tree_text(retrieve_context: RetrieveContext, origin_slice_map: dict[str, DocOriginSchema], paragraph_meta_tree_map: dict[str, DocParagraphMetaTreeSchema]) -> str:

    def _traverse(meta_tree: DocParagraphMetaTreeSchema):
        texts = [
            _traverse(child) for child in meta_tree.children
        ]
        texts = duplicates_list(texts)
        content = origin_slice_map[meta_tree.origin_slice_uuid].content_md or origin_slice_map[meta_tree.origin_slice_uuid].content_html
        return "#" * meta_tree.level + " " + content + "\n" + "\n".join(texts)

    if not retrieve_context or not retrieve_context.origin:
        return ""
    if isinstance(retrieve_context.origin, DocTableRowSchema):
        return retrieve_context.origin_slice.content_md
    elif isinstance(retrieve_context.origin, DocParagraphMetaTreeSchema):
        return _traverse(retrieve_context.origin)
    else:
        # retrieve_context.origin: DocParagraphSchema
        meta_node = paragraph_meta_tree_map[retrieve_context.origin.uuid]
        return _traverse(meta_node)


def top_p(retrieve_contexts: list[RetrieveContext], top_p_score) -> list[RetrieveContext]:
    tt_score = sum([retrieval_info.rerank_score_before_llm for retrieval_info in retrieve_contexts])
    top_p_score_this, results = 0.0, []
    for retrieval_info in retrieve_contexts:
        if top_p_score >= top_p_score_this:
            results.append(retrieval_info)
            top_p_score_this += retrieval_info.rerank_score_before_llm / tt_score
        else:
            break
    return results


def truncation_by_token_limit(retrieve_contexts: list[RetrieveContext], max_length) -> list[RetrieveContext]:
    if retrieve_contexts == []:
        return retrieve_contexts

    first_text = retrieve_contexts[0].tree_text
    if len(first_text) > max_length:
        retrieve_contexts[0].tree_text = retrieve_contexts[0].tree_text[:max_length]
        return retrieve_contexts[0:1]

    filter_retrieve_contexts = []
    remain_length = max_length
    for r in retrieve_contexts:
        if remain_length >= len(r.tree_text):
            remain_length -= len(r.tree_text)
            filter_retrieve_contexts.append(r)
        else:
            filter_retrieve_contexts.append(r)
            break

    return filter_retrieve_contexts
