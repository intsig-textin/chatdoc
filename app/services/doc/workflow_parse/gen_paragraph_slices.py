import logging
import traceback
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.exceptions.http.doc import GenParagraphSlicesException
from app.schemas.doc import CatalogTreeSchema, DocParagraphSchema

from app.services.doc.workflow_parse.schemas import Context
from app.support.helper import log_duration, uuid_base62
from app.support.transform import is_financial_string, markdown2list, uneven_list_to_markdown_table


@log_duration()
def gen_paragraph_slices(context: Context) -> List[DocParagraphSchema]:
    try:
        paragraph_slices = create_paragraph_slices(context.catalog_tree.tree[0])
        return paragraph_slices

    except Exception as e:
        logging.error(f'gen_paragraph_slices error: {e}, {traceback.format_exc()}')
        raise GenParagraphSlicesException()


def create_paragraph_slices(node: CatalogTreeSchema.TreeNode, parent_uuid: str = "", level: int = 1, titles=[]) -> list[DocParagraphSchema]:
    """
    递归地将CatalogTreeSchema.TreeNode转换为DocParagraphSchema列表。

    :param node: 当前处理的CatalogTreeSchema.TreeNode节点。
    :param parent_uuid: 父DocParagraphSchema的uuid，默认为空字符串表示根节点。
    :param level: 当前节点在树中的层级，默认为1。
    :return: 由当前节点及其子节点生成的DocParagraphSchema列表。
    """
    paragraph_slices = []
    content = "\n".join(node.content)

    # 处理带有子节点的Heading节点【目录除外】
    if node.children and content.strip().replace(" ", "") != "目录":
        paragraph_slice = DocParagraphSchema(
            uuid=uuid_base62(),  # 生成唯一uuid
            origin_slice_uuid=node.origin_slice_uuid,
            type=node.label.lower(),
            parent_uuid=parent_uuid,
            embed_text=gen_embedding_text(titles, content),
            level=level,
            token_length=len(content),
            tree_token_length=len(content)
        )
        child_level = level + 1
        child_titles = titles if node.label == "Root" else titles + [content]
        for child in node.children:
            child_paragraph_slices = create_paragraph_slices(child, paragraph_slice.uuid, child_level, child_titles)
            # 包含了所有子树的节点
            paragraph_slices.extend(child_paragraph_slices)
            # 仅获取第一层的子节点uuid
            paragraph_slice.children_uuids.extend([f.uuid for f in child_paragraph_slices if f.parent_uuid == paragraph_slice.uuid])
            paragraph_slice.tree_token_length += sum(f.tree_token_length for f in child_paragraph_slices if f.parent_uuid == paragraph_slice.uuid)

        paragraph_slices.append(paragraph_slice)

    elif node.label == "Text":   # 处理叶子节点text
        chunks, offsets = split_with_offsets(content, chunk_size=500, chunk_overlap=20)
        paragraph_slices.extend(
            DocParagraphSchema(
                uuid=uuid_base62(),  # 生成唯一uuid
                origin_slice_uuid=node.origin_slice_uuid,
                type=node.label.lower(),  # text | table | title
                parent_uuid=parent_uuid,
                children_uuids=[],
                embed_text=gen_embedding_text(titles, chunk),
                level=level,
                token_length=len(chunk),
                tree_token_length=len(chunk),
                leaf=True,
                leaf_properties=DocParagraphSchema.LeafProperties(
                    l_idx=idx + 1,
                    l_num=len(chunks),
                    l_p_start=start_offset,
                    l_p_end=start_offset + len(chunk) - 1,
                )

            ) for idx, (chunk, start_offset) in enumerate(zip(chunks, offsets))
        )

    elif node.label == "Table":  # 处理叶子节点table
        sub_tables = split_table_by_token_limit(content, token_limit=1000)
        paragraph_slices.extend(
            DocParagraphSchema(
                uuid=uuid_base62(),  # 生成唯一uuid
                origin_slice_uuid=node.origin_slice_uuid,
                type=node.label.lower(),  # text | table | title
                parent_uuid=parent_uuid,
                children_uuids=[],
                embed_text=gen_embedding_text(titles, _markdown_str),
                level=level,
                token_length=len(_markdown_str),
                tree_token_length=len(_markdown_str),
                leaf=True,
                leaf_properties=DocParagraphSchema.LeafProperties(
                    l_idx=_idx + 1,
                    l_num=len(sub_tables),
                    l_t_title_row_id=_title_row_idx,
                    l_t_start_row_id=_start_row_idx,
                    l_t_end_row_id=_end_row_idx,
                )

            ) for _idx, (_title_row_idx, _start_row_idx, _end_row_idx, _markdown_str) in enumerate(sub_tables)
        )

    return paragraph_slices


def split_with_offsets(text, chunk_size, chunk_overlap):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_text(text)
    offsets = []
    current_offset = 0

    for chunk in chunks:
        chunk_start = current_offset
        current_offset += len(chunk) - chunk_overlap  # 减去重叠部分
        offsets.append(chunk_start)

    return chunks, offsets


def split_table_by_token_limit(table_markdown: str, token_limit: int = 1000):

    table_list = markdown2list(table_markdown)

    sub_tables = []
    sub_table = []
    title_row_idx = start_row_idx = 0
    title_row = None
    for row_id, row in enumerate(table_list):
        row = [x if not is_financial_string(x) else "" for x in row]
        if not row:
            continue

        if not title_row:
            title_row = row
            title_row_idx = row_id
            continue

        if not sub_table:
            sub_table = [title_row, row]
            start_row_idx = row_id
            continue

        if len(uneven_list_to_markdown_table(sub_table + [row], fill_value="-")) > token_limit:
            markdown_str = uneven_list_to_markdown_table(sub_table, fill_value="-")
            sub_tables.append(
                (title_row_idx, start_row_idx, row_id - 1, markdown_str)
            )
            sub_table = []

        else:
            sub_table.append(row)

    if sub_table:
        sub_tables.append(
            (title_row_idx, start_row_idx, len(table_list) - 1, uneven_list_to_markdown_table(sub_table, fill_value="-"))
        )

    if not sub_tables:
        sub_tables = [(
            (title_row_idx, title_row_idx, title_row_idx, table_markdown)
        )]

    return sub_tables


def gen_embedding_text(titles, text, start_level=2):
    """
    在给定文本的开始处添加多个Markdown格式的标题。

    参数:
    titles (List[str]): 标题内容的列表。
    text (str): 原始文本内容。
    start_level (int): 开始的标题级别，默认为2（二级标题）。

    返回:
    str: 添加了Markdown标题的新文本。
    """

    # titles = titles[1:] if titles and titles[0] == "Root" else titles

    # markdown_title = ""

    # # 遍历标题列表，为每个标题添加Markdown格式
    # for idx, title in enumerate(titles, start=start_level):
    #     # 确保标题内容安全
    #     sanitized_title = title.replace("#", "\\#")
    #     # 添加相应级别的标题，根据列表索引动态调整级别
    #     markdown_title += "#" * idx + " " + sanitized_title + "\n"

    # return markdown_title + text
    return text
