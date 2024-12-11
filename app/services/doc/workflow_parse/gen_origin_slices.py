import logging
import re
import traceback
from typing import List, Tuple

from app.exceptions.http.doc import GenOriginSlicesException
from app.schemas.doc import CatalogTreeSchema, DocOriginSchema

from app.services.doc.workflow_parse.schemas import Context
from app.support.helper import log_duration, uuid_base62
from app.support.transform import html2markdown


@log_duration()
def gen_origin_slices(context: Context) -> List[DocOriginSchema]:
    try:
        origin_slices, catalog_tree_nodes = doctree_dfs(context.catalog_tree.tree[0])
        for origin_slice, catalog_tree_node in zip(origin_slices, catalog_tree_nodes):
            if origin_slice.type == "table":
                markdown_str_list = [html2markdown(html) for html in merge_table_htmls(origin_slice.content_html)]
                markdown_str = "\n".join(markdown_str_list)
                origin_slice.content_md = markdown_str
                # 修改context, catalog_tree_node.content 为markdown字符串
                catalog_tree_node.content = [markdown_str]

        return origin_slices

    except Exception as e:
        logging.error(f'gen_origin_slices error: {e}, {traceback.format_exc()}')
        raise GenOriginSlicesException()


def doctree_dfs(doctree_node: CatalogTreeSchema.TreeNode, titles=[]) -> Tuple[List[DocOriginSchema], List[CatalogTreeSchema.TreeNode]]:
    _type = "paragraph"
    for _content in doctree_node.content:
        if _content.startswith("<table border="):
            _type = "table"
            break

    if _type == "table":
        content = doctree_node.content  # content is list, 后续需要处理
    else:
        content = "\n".join(doctree_node.content)

    origin_item = DocOriginSchema(
        uuid=uuid_base62(),
        titles=titles,
        ori_ids=doctree_node.ori_ids,
        # content_md=content,
        content_html=content,
        type=_type,
    )
    # 设置对应关系，到origin_item的uuid，构造PARAGRAPH的时候需要使用上
    doctree_node.origin_slice_uuid = origin_item.uuid
    r1, r2 = [origin_item], [doctree_node]
    if doctree_node.children:
        if isinstance(content, list):
            content = content[0] if content else ""
        child_titles = titles + [re.sub(r'[第一二三四五六七八九十零壹贰叁肆伍陆柒捌玖拾章节、（）()0123456789. ]', '', content)]
        for child in doctree_node.children:
            _r1, _r2 = doctree_dfs(child, titles=child_titles)
            r1.extend(_r1)
            r2.extend(_r2)

    return r1, r2


def merge_table_htmls(htmls) -> list[str]:
    """
    合并表格，合并逻辑为连续的表格进行合并
    :param lst:
    :return:
    """

    def end_id(i, htmls):
        while i < len(htmls) - 1:
            if """<table border="1">""" in htmls[i] and """<table border="1">""" in htmls[i + 1]:
                i += 1
            else:
                break
        return i

    result = []
    i = 0
    while i < len(htmls):
        if """<table border="1">""" in htmls[i]:
            j = end_id(i, htmls)
            result.append("""<table border="1">"""
                          + "".join([r.replace("""<table border="1">""", "").replace("""</table>""", "") for r in htmls[i:j + 1]])
                          + """</table>""")
            i = j + 1
        else:
            result.append(htmls[i])
            i += 1
    return result
