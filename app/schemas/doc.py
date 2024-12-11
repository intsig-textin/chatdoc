from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel


class FileParseRequest(BaseModel):
    file_name: str
    file_type: str
    file_url: str


class FileMetaSchema(BaseModel):
    file_name: str
    file_id: str
    keywords: list[str] = []
    paragraph_slices_meta: Optional["DocParagraphMetaTreeSchema"] = None
    thumbnail: str = ""
    extra: Optional[dict] = None
    created_at: datetime = datetime.now()


class FileParseResponse(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    file_meta: Optional[FileMetaSchema]


class FileDeleteResponse(BaseModel):
    file_delete_count: int
    origin_slice_delete_count: int
    table_slice_delete_count: int
    paragraph_slice_delete_count: int


class FileListResponse(BaseModel):
    files: List[FileMetaSchema]  # 文件元数据列表


class Pdf2MdSchema(BaseModel):
    class Metric(BaseModel):
        angle: int
        dpi: int = -1
        duration: float
        image_id: str = ""
        page_id: int
        page_image_height: int
        page_image_width: int
        status: str

    class Page(BaseModel):  # 信息暂且用不到
        pass

    class Detail(BaseModel):
        content: int                # content的id
        outline_level: int          # 层级, 从 -1 开始
        page_id: int                # 页码, 从1开始
        paragraph_id: int           # 元素id, 从 0 开始
        position: List[int]         # [左上x, 左上y, 右上x, 右上y, 右下x, 右下y, 左下x, 左下y]
        text: str
        type: str                   # paragraph | table
        _tree_level: int = -1       # 空字段，后处理加上
        _label: str = ""            # 空字段，后处理加上

    class ResultData(BaseModel):
        # pages: List[Page]  # 如果需要激活此字段，取消注释
        pages: List[dict]    # 直接解析即可
        detail: List['Pdf2MdSchema.Detail']
        # markdown: str  # 如果需要激活此字段，取消注释
        # success_count: int  # 如果需要激活此字段，取消注释
        # total_count: int  # 如果需要激活此字段，取消注释
        # total_page_count: int  # 如果需要激活此字段，取消注释
        # valid_page_count: int  # 如果需要激活此字段，取消注释

    result: ResultData
    metrics: List[Metric]
    version: str
    duration: int
    code: int


class CatalogTreeSchema(BaseModel):

    class TreeNode(BaseModel):
        label: str = ""  # Root|Text|Heading|Table
        pos: list[int] = []
        ori_ids: list[str] = []  # 段落唯一标识集合"page_id-1, paragraph_id"，可能会包含多个，["0,0", ...]
        content: list[str] = []
        children: list["CatalogTreeSchema.TreeNode"] = []
        tree_level: int = 0  # 节点所在树的深度，Root节点为-1，以下从0开始
        page_id: int = 0  # 页码，从1开始
        origin_slice_uuid: str = ""  # 对应原始slice的uuid

    class TreeGenerateNode(BaseModel):
        content: str = ""
        pageNum: int = -1
        pos: list[int] = []
        level: int = -1

    tree: list["CatalogTreeSchema.TreeNode"] = []
    generate: list["CatalogTreeSchema.TreeGenerateNode"] = []


class DocOriginSchema(BaseModel):
    """
    文档原文，通过ori_ids可以获取到文章原文内容
    """
    uuid: str = ""                      # 切片唯一标识uuid
    file_uuid: str = ""                 # 切片对应的file_uuid
    titles: list[str] = []
    ori_ids: list[str] = []             # 切片对应到原文档的溯源为止
    content_md: Union[str, list] = ""   # 段落内容 | 表格markdown内容
    content_html: Union[str, list] = ""  # 段落内容 | 表格html内容
    type: str = ""


class DocTableRowSchema(BaseModel):
    uuid: str = ""                      # 切片唯一标识uuid
    file_uuid: str = ""
    title: str = ""
    origin_slice_uuid: str = ""
    row_id: int = -1
    keywords: list[str] = []
    embed_text: str = ""


class DocParagraphSchema(BaseModel):
    class LeafProperties(BaseModel):
        l_idx: int = 1              # leaf 节点切分的节点index，从1开始
        l_num: int = 1              # leaf 节点切分的节点总数
        l_p_start: int = 0          # 起始偏移【相对ori_id中的偏移】
        l_p_end: int = 0            # 结束偏移

        l_t_title_row_id: int = 0   # 表格标题行
        l_t_start_row_id: int = 0   # 表格起始行
        l_t_end_row_id: int = 0     # 表格结束行

    uuid: str = ""                  # 切片唯一标识uuid
    file_uuid: str = ""             # 切片对应的file_uuid
    origin_slice_uuid: str = ""     # 对应origin_slice的uuid
    type: str = "text"              # 切片类型 text | table | title
    embed_text: str = ""            # 用于emebedding的text

    parent_uuid: str = ""           # 父级片段uuid
    children_uuids: list[str] = []  # 子级片段uuid

    tree_token_length: int = 0      # 节点及子节点token长度
    token_length: int = 0           # 当前节点token长度
    level: int = 1                  # 切片所在文档树level，从1开始

    # ---- leaf切片属性 ----
    leaf: bool = False                      # 是否是叶子节点
    leaf_properties: Optional[LeafProperties] = None  # 叶子节点属性
    # ---- embedding值 ----
    embedding: list[float] = []             # 临时变量，避免占用内存，用完即释放


class DocParagraphMetaTreeSchema(BaseModel):
    """
    存入ES中的结构，用于Small2Big扩充使用，所以仅存一些Small2Big中用到的关键属性即可，存入到file表当中
    """
    uuid: str = ""                  # 切片唯一标识uuid
    origin_slice_uuid: str = ""     # 对应origin_slice的uuid
    leaf: bool = False              # 是否叶子切片
    children: list["DocParagraphMetaTreeSchema"]   # 子节点
    level: int = 1                  # 切片所在文档树level，从1开始
    tree_token_length: int = 0      # 节点及子节点token长度
    token_length: int = 0           # 当前节点token长度

    @classmethod
    def from_paragraphs(cls, paragraphs: list[DocParagraphSchema]):
        """
        从一组 DocParagraphSchema 对象构建树形结构
        :param paragraphs: 文档段落列表
        :return: 树形结构的根节点列表
        """
        # 创建一个映射表，uuid -> 节点对象
        uuid_map = {p.uuid: cls(uuid=p.uuid, origin_slice_uuid=p.origin_slice_uuid, leaf=p.leaf, children=[], level=p.level,
                                tree_token_length=p.tree_token_length, token_length=p.token_length)
                    for p in paragraphs}

        roots = []  # 用于存储根节点
        for paragraph in paragraphs:
            current_node = uuid_map[paragraph.uuid]
            if paragraph.parent_uuid:
                # 找到父节点并添加到其子节点列表
                parent_node = uuid_map.get(paragraph.parent_uuid)
                if parent_node:
                    parent_node.children.append(current_node)
            else:
                # 如果没有父节点，则认为是根节点
                roots.append(current_node)

        return roots[0] if roots else None

    def to_paragraph_meta_map(self) -> dict[str, "DocParagraphMetaTreeSchema"]:
        """
        将树形结构转换为一个以 uuid 为键的映射表，方便快速查找。
        :return: 以 uuid 为键的段落元数据映射表
        """
        meta_map = {}

        def traverse(node: "DocParagraphMetaTreeSchema"):
            # 添加当前节点到映射表
            meta_map[node.uuid] = node
            # 递归处理子节点
            for child in node.children:
                traverse(child)

        # 开始遍历树的根节点
        traverse(self)
        return meta_map
