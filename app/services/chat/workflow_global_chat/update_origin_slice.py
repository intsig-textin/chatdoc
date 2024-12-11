import logging
import traceback
from app.exceptions.http.global_chat import UpdateOriginSliceException
from app.schemas.elasticsearch import ESFile, ESOriginSlice
from app.services.chat.workflow_global_chat.schemas import Context, RetrieveContext
from app.support import xjson
from app.support.helper import log_duration
from app.schemas.doc import DocOriginSchema, DocTableRowSchema, DocParagraphSchema, DocParagraphMetaTreeSchema, FileMetaSchema


@log_duration()
def update_origin_slice(context: Context) -> tuple[dict[str, DocOriginSchema], dict[str, DocParagraphMetaTreeSchema]]:
    try:
        origin_slice_uuids = set()
        origin_slice_uuids = origin_slice_uuids.union(get_table_slice_uuids(context.table_retrieve_results))

        paragraph_meta_tree_map = dict()
        file_meta_list = fillup_file_meta_slices(context.final_files)
        for file_meta in file_meta_list:
            if file_meta.paragraph_slices_meta:
                paragraph_meta_tree_map.update(file_meta.paragraph_slices_meta.to_paragraph_meta_map())

        origin_slice_uuids = origin_slice_uuids.union(get_paragraph_slice_uuids(context.paragraph_retrieve_results, paragraph_meta_tree_map))

        es_origin_slices: list[ESOriginSlice] = ESOriginSlice.search().extra(size=1.2 * len(origin_slice_uuids)).filter("terms", **{"uuid.keyword": list(origin_slice_uuids)}).execute().hits

        origin_slice_map = {
            es_origin_slice.uuid: es_origin_slice.to_schema()
            for es_origin_slice in es_origin_slices
        }

        fillup_retrieve_contexts(context.retrieve_contexts, origin_slice_map, paragraph_meta_tree_map)

        return origin_slice_map, paragraph_meta_tree_map
    except Exception as e:
        logging.error(f'update_origin_slice error: {e}, {traceback.format_exc()}')
        raise UpdateOriginSliceException()


def fillup_file_meta_slices(file_meta_list: list[FileMetaSchema]) -> list[FileMetaSchema]:
    # 需要去重
    meta_mapper = {
        _f.file_id: _f for _f in file_meta_list
    }
    result = []
    if meta_mapper:
        es_files: list[ESFile] = ESFile.search().extra(
            _source=["uuid", "paragraph_slices_meta"],
            size=1.2 * len(meta_mapper),
        ).filter("terms", **{"uuid.keyword": list(meta_mapper.keys())}).execute().hits
        slice_mapper = {
            es_file.uuid: es_file.paragraph_slices_meta
            for es_file in es_files
        }
        for file_id, _f in meta_mapper.items():
            if file_id in slice_mapper:
                paragraph_slices_meta = None
                if slice_mapper[file_id]:
                    paragraph_slices_meta_dict = xjson.loads(slice_mapper[file_id])
                    if paragraph_slices_meta_dict:
                        paragraph_slices_meta = DocParagraphMetaTreeSchema.model_validate(paragraph_slices_meta_dict)
                _f.paragraph_slices_meta = paragraph_slices_meta
                result.append(_f)

    return result


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


def fillup_retrieve_contexts(retrieve_contexts: list[RetrieveContext], origin_slice_map: dict[str, DocOriginSchema], paragraph_meta_tree_map: dict[str, DocParagraphMetaTreeSchema]):
    def _get_tree_slices(node: DocParagraphMetaTreeSchema):
        node_slice = origin_slice_map[node.origin_slice_uuid]
        slices = [node_slice]
        for child in node.children:
            slices.extend(_get_tree_slices(child))
        return slices

    for r_context in retrieve_contexts:
        origin = r_context.origin
        r_context.origin_slice = origin_slice_map[origin.origin_slice_uuid]
        if isinstance(origin, DocTableRowSchema):
            r_context.tree_slices = [r_context.origin_slice]
        elif isinstance(origin, DocParagraphSchema):
            r_context.tree_slices = _get_tree_slices(paragraph_meta_tree_map[origin.uuid])
