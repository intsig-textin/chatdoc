import logging
import traceback
from app.exceptions.http.chat import UpdateOriginSliceException
from app.schemas.elasticsearch import ESOriginSlice
from app.services.chat.workflow_chat.schemas import Context
from app.support.helper import log_duration
from app.schemas.doc import DocOriginSchema, DocTableRowSchema, DocParagraphSchema, DocParagraphMetaTreeSchema


@log_duration()
def update_origin_slice(context: Context) -> tuple[dict[str, DocOriginSchema], dict[str, DocParagraphMetaTreeSchema]]:
    try:
        origin_slice_uuids = set()
        origin_slice_uuids = origin_slice_uuids.union(get_table_slice_uuids(context.table_retrieve_results))

        paragraph_meta_tree_map = dict()
        for file_meta in context.file_meta_list:
            if file_meta.paragraph_slices_meta:
                paragraph_meta_tree_map.update(file_meta.paragraph_slices_meta.to_paragraph_meta_map())

        origin_slice_uuids = origin_slice_uuids.union(get_paragraph_slice_uuids(context.paragraph_retrieve_results, paragraph_meta_tree_map))

        es_origin_slices: list[ESOriginSlice] = ESOriginSlice.search().extra(size=1.2 * len(origin_slice_uuids)).filter("terms", **{"uuid.keyword": list(origin_slice_uuids)}).execute().hits

        origin_slice_map = {
            es_origin_slice.uuid: es_origin_slice.to_schema()
            for es_origin_slice in es_origin_slices
        }

        return origin_slice_map, paragraph_meta_tree_map
    except Exception as e:
        logging.error(f'update_origin_slice error: {e}, {traceback.format_exc()}')
        raise UpdateOriginSliceException()


def get_table_slice_uuids(table_slices: list[DocTableRowSchema]) -> set[str]:
    origin_slice_uuids = set()
    for table_slice in table_slices:
        origin_slice_uuids.add(table_slice.origin_slice_uuid)

    return origin_slice_uuids


def get_paragraph_slice_uuids(paragraph_slices: list[DocParagraphSchema], paragraph_meta_tree_map: dict[str, DocParagraphMetaTreeSchema]) -> set[str]:
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
    for paragraph_slice in paragraph_slices:
        meta_node = paragraph_meta_tree_map.get(paragraph_slice.uuid)
        traverse(meta_node)

    return origin_slice_uuids
