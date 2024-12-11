from itertools import groupby
import logging
import traceback

from app.exceptions.http.doc import CatalogException
from app.schemas.doc import CatalogTreeSchema, Pdf2MdSchema

from app.services.doc.workflow_parse.schemas import Context
from app.support.helper import log_duration


@log_duration()
def catalog(context: Context) -> CatalogTreeSchema:
    try:
        if is_ppt(context):
            tree = build_tree_by_page(context.pdf2md_result.result.detail)
            catalog = CatalogTreeSchema(tree=[tree], generate=[])

        else:
            new_detail = detail_process(context.pdf2md_result.result.detail, keep_hierarchy=False)
            tree = TreeBuild(new_detail)
            catalog = CatalogTreeSchema(tree=[tree], generate=tree_generate(tree))

        if len(catalog.tree) == 0:
            raise Exception("目录树解析为空")

        return catalog

    except Exception as e:
        logging.error(f'catalog error: {e}, {traceback.format_exc()}')
        raise CatalogException()


def is_ppt(context: Context):
    page_metrics = context.pdf2md_result.metrics

    flat_pages_count = sum([1 if page.page_image_height < page.page_image_width else 0 for page in page_metrics])
    is_ppt = page_metrics and flat_pages_count / len(page_metrics) >= 0.8
    return is_ppt


def build_tree_by_page(md_detail: list[Pdf2MdSchema.Detail]):
    """
    Args:
        md_detail: pdf2md的结果

    Returns:
        按页切分建树的结果

    """
    # 构造基础目录树
    tree = CatalogTreeSchema.TreeNode(
        label="Root",
        page_id=0,
        pos=[0, 0, 1, 0, 1, 1, 0, 1],
        ori_ids=["-1,-1"],
        content=["Root"],
        tree_level=0
    )
    # 去掉页眉页脚
    md_detail = [d for d in md_detail if d.content != 1 or d.text.strip() != ""]
    grouped_data = groupby(md_detail, key=lambda x: x.page_id)
    for page_id, group in grouped_data:
        page = CatalogTreeSchema.TreeNode(page_id=page_id)
        grouped_items = list(group)
        for ind, item in enumerate(grouped_items):
            if ind == 0:
                page.label = "Heading"
                page.pos = item.position
                page.ori_ids = [str(item.page_id - 1) + "," + str(item.paragraph_id)]
                page.content = [item.text]
                page.tree_level = 1
            else:
                leaf_node = CatalogTreeSchema.TreeNode(page_id=page_id)
                leaf_node.label = "Table" if item.type == "table" else "Text"
                leaf_node.pos = item.position
                leaf_node.ori_ids = [
                    str(item.page_id - 1) + "," + str(item.paragraph_id)]
                leaf_node.content = [item.text]
                leaf_node.tree_level = 2
                page.children.append(leaf_node)
        tree.children.append(page)

    return tree


def detail_process(md_detail: list[Pdf2MdSchema.Detail], keep_hierarchy=False):
    """
    Args:
        md_detail: pdf2md的结果

    Returns:
        按阅读顺序建树的结果
    """
    def remove_title(title):
        key_info = ["表", "图", "Fig", "FIG", "fig", "Table", "TABLE", "table"]
        res = [k for k in key_info if k in title]
        if res != []:
            return True
        else:
            return False

    label_dic = {"paragraph": "Text", "image": "Text", "table": "Table"}
    new_detail = [Pdf2MdSchema.Detail(
        tags=[],
        paragraph_id=-1,
        page_id=0,
        content=1,
        outline_level=-1,
        position=[0, 0, 1, 0, 1, 1, 0, 1],
        text="Root",
        type="root",
    )]
    new_detail[0]._tree_level = -1

    # 用来记录层级
    tree_level = -1  # root节点
    for d in md_detail:
        if d.content == 1 or d.text.strip() == "":
            continue
        # 上级节点为Root时，第一个出现的标题节点层级应该为0，纠正模型预的层级结果
        if tree_level == -1 and d.outline_level not in [0, -1]:
            d.outline_level = 0
        if tree_level == -1:
            # 上文未出现过标题，所有的节点都是一级层级
            d._tree_level = 0
            d._label = label_dic[d.type]
        if d.outline_level != -1:
            if keep_hierarchy:
                d._tree_level = d.outline_level
                tree_level = d.outline_level
            else:
                d._tree_level = 0
                tree_level = 0
            d._label = "Heading"
            # 非标题节点为下一级，且将 表格标题与图片标题 去除层级
        if tree_level != -1 and (d.outline_level == -1 or remove_title(d.text)):
            d._tree_level = tree_level + 1
            d._label = label_dic[d.type]

        new_detail.append(d)

    return new_detail


def TreeBuild(preorder: list[Pdf2MdSchema.Detail]):
    if not preorder:
        return None

    root = CatalogTreeSchema.TreeNode(
        content=[preorder[0].text],
        page_id=preorder[0].page_id,
        tree_level=preorder[0]._tree_level + 1,
        label=preorder[0]._label,
        pos=preorder[0].position,
        ori_ids=[str(preorder[0].page_id - 1) + ","
                 + str(preorder[0].paragraph_id)]
    )
    stack = [(root, root.tree_level - 1)]

    for ind, p in enumerate(preorder[1:]):
        depth = preorder[ind + 1]._tree_level
        while stack and stack[-1][1] >= depth:
            stack.pop()

        node = CatalogTreeSchema.TreeNode(
            content=[p.text],
            page_id=p.page_id,
            tree_level=p._tree_level + 1,
            label=p._label,
            pos=p.position,
            ori_ids=[str(p.page_id - 1) + "," + str(p.paragraph_id)]
        )
        if stack:
            stack[-1][0].children.append(node)
        stack.append((node, depth))

    return root


def tree_generate(tree: CatalogTreeSchema.TreeNode):

    result = []
    if tree.children:
        if tree.tree_level > 0:
            result.append(
                CatalogTreeSchema.TreeGenerateNode(
                    content=tree.content[0] if tree.content else "",
                    pageNum=tree.page_id,
                    pos=tree.pos,
                    level=tree.tree_level)
            )
        for child in tree.children:
            result.extend(
                tree_generate(child)
            )

    return result
