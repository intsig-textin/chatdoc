import logging
import traceback
from app.exceptions.http.chat import Small2BigException
from app.schemas.elasticsearch import ESOriginSlice
from app.services.chat.workflow_chat.schemas import Context, RetrieveContext
from app.support.helper import group_by_func, log_duration
from app.schemas.doc import DocParagraphMetaTreeSchema, DocParagraphSchema, DocOriginSchema


@log_duration()
def small2big(context: Context) -> list[RetrieveContext]:
    """
    贪婪获取父子切片合并
    """
    try:
        # 多文档时候处理，确保每个文件有一个召回
        # A1 B1 C1 之后就按照 rerank分数来获取
        retrieve_contexts = sort_by_multiple_documents(context)
        need_expand_r_contexts = [r_context for r_context in retrieve_contexts if need_expand(r_context)]
        # 填充origin_slices到context.origin_slice_map当中
        parent_meta_tree_list = [context.paragraph_meta_tree_map[r_context.origin.parent_uuid] for r_context in need_expand_r_contexts]
        context.origin_slice_map.update(fillup_slice_mapper(context, parent_meta_tree_list))
        # 开始判断是否使用当前节点Or父结点
        new_r_contexts = []
        # 贪婪去添加片段
        for r_context in retrieve_contexts:
            # 与之前节点有ori_id重合，则不添加进去
            if has_intersect(r_context, new_r_contexts):
                continue
            if r_context in need_expand_r_contexts:
                parent_meta = context.paragraph_meta_tree_map[r_context.origin.parent_uuid]
                parent_slice = context.origin_slice_map.get(parent_meta.origin_slice_uuid)
                pr_context = RetrieveContext(
                    origin=parent_meta,
                    question_rerank_score=r_context.question_rerank_score,
                    retrieve_rank_score=r_context.retrieve_rank_score,
                    repeat_score=r_context.repeat_score,
                    rerank_score_before_llm=r_context.rerank_score_before_llm,
                    retrieval_type="paragraph",
                    origin_slice=parent_slice,
                    tree_slices=get_tree_slices(context, parent_meta),
                )
                # 如果之前已经添加过了，则不再单独添加了！
                if not has_intersect(pr_context, new_r_contexts):
                    new_r_contexts.append(pr_context)
            else:
                new_r_contexts.append(r_context)

        return new_r_contexts

    except Exception as e:
        logging.error(f'small2big error: {e}, {traceback.format_exc()}')
        raise Small2BigException()


def need_expand(r_context: RetrieveContext) -> bool:
    """
    判断是否需要扩展
    # 1. 段落小于2000token，2. 存在父结点，且为叶子节点，3. 节点level>2，即父结点不会到Root节点；4. 否则使用当前节点
    """
    if not isinstance(r_context.origin, DocParagraphSchema):
        return False

    if r_context.origin.tree_token_length >= 2000:
        return False

    if not r_context.origin.parent_uuid:
        return False

    if not r_context.origin.leaf:
        return False

    if r_context.origin.level <= 2:
        return False

    return True


def sort_by_multiple_documents(context: Context) -> list[RetrieveContext]:
    '''
    description: # 超过3份文档, 每份文档召回取top3
    return {*}
    '''
    if len(context.file_meta_list) < 4:
        first_contexts = [r_contexts[0] for file_uuid, r_contexts in group_by_func(context.retrieve_contexts, keyfunc=lambda x: x.origin_slice.file_uuid) if r_contexts]

        other_contexts = [
            _context for _context in context.retrieve_contexts if _context not in first_contexts
        ]
        new_retieve_list = first_contexts + other_contexts
    else:
        new_retieve_list = [r_contexts[0:3] for file_uuid, r_contexts in group_by_func(context.retrieve_contexts, keyfunc=lambda x: x.origin_slice.file_uuid) if r_contexts]
        new_retieve_list = [item for sub_list in new_retieve_list for item in sub_list]

    return new_retieve_list


def has_intersect(r_context: RetrieveContext, last_r_contexts: list[RetrieveContext]) -> bool:
    for pre_context in last_r_contexts:
        if r_context.intersect(pre_context):
            return True
    return False


def get_tree_slices(context: Context, node: DocParagraphMetaTreeSchema):
    node_slice = context.origin_slice_map[node.origin_slice_uuid]
    slices = [node_slice]
    for child in node.children:
        slices.extend(get_tree_slices(context, child))
    return slices


def fillup_slice_mapper(context: Context, paragraph_slice_metas: list[DocParagraphMetaTreeSchema]) -> dict[str, DocOriginSchema]:
    """
    填充origin_slices到context.origin_slice_map当中
    """
    origin_slice_uuids = get_paragraph_slice_uuids(paragraph_slice_metas, context.paragraph_meta_tree_map)
    origin_slice_uuids -= context.origin_slice_map.keys()
    es_origin_slices: list[ESOriginSlice] = ESOriginSlice.search().extra(size=1.2 * len(origin_slice_uuids)).filter("terms", **{"uuid.keyword": list(origin_slice_uuids)}).execute().hits

    origin_slice_map = {
        es_origin_slice.uuid: es_origin_slice.to_schema()
        for es_origin_slice in es_origin_slices
    }

    return origin_slice_map


def get_paragraph_slice_uuids(paragraph_slice_metas: list[DocParagraphMetaTreeSchema], paragraph_meta_tree_map: dict[str, DocParagraphMetaTreeSchema]) -> set[str]:
    """
    将树形结构转换为一个以 uuid 为键的映射表，方便快速查找。
    :return: 以 uuid 为键的段落元数据映射表
    """
    origin_slice_uuids = set()

    def traverse(meta_node: DocParagraphMetaTreeSchema):
        if meta_node:
            # 添加当前节点到映射表
            origin_slice_uuids.add(meta_node.origin_slice_uuid)
            # 递归处理子节点
            for child in meta_node.children:
                traverse(child)

    # 开始遍历召回到的节点的子节点数据原文本获取
    for meta_node in paragraph_slice_metas:
        traverse(meta_node)

    return origin_slice_uuids
