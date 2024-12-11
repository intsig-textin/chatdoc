from datetime import datetime
from elasticsearch_dsl import DenseVector, Document, Object, Text, Keyword, Integer, Date, Boolean

from app.schemas.doc import DocOriginSchema, DocParagraphSchema, DocTableRowSchema, FileMetaSchema, DocParagraphMetaTreeSchema
from app.support import xjson
from config.config import settings


class ESFile(Document):
    uuid = Keyword(ignore_above=100)
    filename = Text()                                   # 文件名称
    keywords = Text(multi=True)                         # 文件关键词
    paragraph_slices_meta = Text(index=False)           # 段落切片meta信息【用于small2big】
    extra = Text(index=False)                           # 文件额外信息【用作前端进行展示】
    thumbnail = Text(index=False)                       # 文件缩略图url
    created_at = Date(format="yyyy-MM-dd HH:mm:ss")     # 创建时间

    class Index:
        name = settings.elasticsearch.index_file   # 定义索引名称
        settings = settings.elasticsearch.index_settings.model_dump()

    @classmethod
    def from_schema(cls, file_meta: FileMetaSchema) -> 'ESFile':
        return cls(
            uuid=file_meta.file_id,
            filename=file_meta.file_name,
            keywords=file_meta.keywords,
            paragraph_slices_meta=xjson.dumps(file_meta.paragraph_slices_meta.model_dump()) if file_meta.paragraph_slices_meta else {},
            created_at=file_meta.created_at,
            extra=xjson.dumps(file_meta.extra),
            thumbnail=file_meta.thumbnail,
        )

    def to_schema(self) -> FileMetaSchema:
        paragraph_slices_meta = None
        if self.paragraph_slices_meta:
            paragraph_slices_meta_dict = xjson.loads(self.paragraph_slices_meta)
            if paragraph_slices_meta_dict:
                paragraph_slices_meta = DocParagraphMetaTreeSchema.model_validate(paragraph_slices_meta_dict)

        extra = xjson.loads(self.extra) if self.extra else None

        return FileMetaSchema(
            file_id=self.uuid,
            file_name=self.filename,
            keywords=self.keywords,
            paragraph_slices_meta=paragraph_slices_meta,
            extra=extra,
            thumbnail=self.thumbnail or "",
            created_at=self.created_at
        )

    @classmethod
    def keys(cls, exclude=[]):
        keys = set(cls._doc_type.mapping.properties.properties.keys())
        return list(keys - set(exclude))

    @classmethod
    def keys_brief(cls):
        return ESFile.keys(exclude=["paragraph_slices_meta", "extra"])


class ESOriginSlice(Document):
    uuid = Keyword(ignore_above=100)                    # slice唯一标识
    file_uuid = Keyword(ignore_above=100)               # 关联文件uuid
    type = Keyword(ignore_above=100)                    # slice类型
    ori_ids = Keyword(ignore_above=100)                 # 原始id，通过原始id可以找到对应的元素
    titles = Text()                                     # 元素的标题
    content_html = Text()                               # 元素内容。源内容【段落|表格是html】
    content_md = Text()                                 # 元素内容。源内容转换后的markdown结果
    created_at = Date(format="yyyy-MM-dd HH:mm:ss")     # 创建时间

    class Index:
        name = settings.elasticsearch.index_origin_slice
        settings = settings.elasticsearch.index_settings.model_dump()

    @classmethod
    def from_schema(cls, origin_slice: DocOriginSchema, file_uuid: str = "") -> 'ESOriginSlice':
        return cls(
            file_uuid=file_uuid,
            uuid=origin_slice.uuid,
            type=origin_slice.type,
            ori_ids=origin_slice.ori_ids,
            titles=origin_slice.titles,
            content_md=origin_slice.content_md,
            content_html=origin_slice.content_html,
            created_at=datetime.now(),
        )

    def to_schema(self) -> DocOriginSchema:
        return DocOriginSchema(
            uuid=self.uuid,
            file_uuid=self.file_uuid,
            type=self.type,
            titles=self.titles,
            content_md=self.content_md,
            content_html=self.content_html,
            ori_ids=self.ori_ids or [],
        )


class ESTableRowSlice(Document):
    uuid = Keyword(ignore_above=100)                    # slice唯一标识
    file_uuid = Keyword(ignore_above=100)               # 关联文件uuid
    origin_slice_uuid = Keyword(ignore_above=100)       # 原始Slice的uuid
    title = Text()                                      # 表格标题
    keywords = Text(multi=True)                         # 表格关键词列表【BM25搜索】 行B字段 list
    embed_text = Text()                                  # 嵌入文本
    row_id = Integer()                                  # 行号
    created_at = Date(format="yyyy-MM-dd HH:mm:ss")     # 创建时间

    class Index:
        name = settings.elasticsearch.index_table_row_slice   # 定义索引名称
        settings = settings.elasticsearch.index_settings.model_dump()

    @classmethod
    def from_schema(cls, table_slice: DocTableRowSchema, file_uuid: str = "") -> 'ESTableRowSlice':
        return cls(
            file_uuid=file_uuid,
            uuid=table_slice.uuid,
            origin_slice_uuid=table_slice.origin_slice_uuid,
            title=table_slice.title,                # 表格标题
            keywords=table_slice.keywords,          # 表格关键词列表【BM25搜索】 行B字段 list
            embed_text=table_slice.embed_text,      # 嵌入文本
            row_id=table_slice.row_id,              # 行号
            created_at=datetime.now(),
        )

    def to_schema(self) -> DocTableRowSchema:
        return DocTableRowSchema(
            file_uuid=self.file_uuid,
            title=self.title,
            uuid=self.uuid,
            origin_slice_uuid=self.origin_slice_uuid,
            row_id=self.row_id,
            keywords=self.keywords,
            embed_text=self.embed_text
        )

    @classmethod
    def keys(cls, exclude=[]):
        keys = set(cls._doc_type.mapping.properties.properties.keys())
        return list(keys - set(exclude))


class ESParagraphSlice(Document):
    file_uuid = Keyword(ignore_above=100)               # 关联文件uuid
    uuid = Keyword(ignore_above=100)                    # 段落uuid
    origin_slice_uuid = Keyword(ignore_above=100)       # 对应原始slice的id
    type = Keyword(ignore_above=100)                    # 段落切片类型 text/table/title
    embed_text = Text()                                  # 嵌入文本【基本不用，一般去拿原文拼接】
    parent_uuid = Keyword(ignore_above=100)             # 父级uuid
    children_uuids = Keyword(ignore_above=100, multi=True)  # 子级uuid列表
    tree_token_length = Integer()                       # 树形结构token长度
    token_length = Integer()                            # 当前节点token长度
    level = Integer()                                   # 切片所在文档树层级，从1开始
    created_at = Date(format="yyyy-MM-dd HH:mm:ss")     # 创建时间
    leaf = Boolean()                                    # 是否叶子切片
    embedding = DenseVector(dim=settings.api.embedding.dimension)  # 嵌入向量

    # ---- leaf切片属性 ----
    leaf_properties = Object(  # Store all leaf-related properties in one object
        properties={
            'l_idx': Integer(),                            # 叶子切片的切分idx
            'l_num': Integer(),                            # 叶子切片的切分总数
            'l_p_start': Integer(),                        # 叶子切片的切分开始偏移位置
            'l_p_end': Integer(),                          # 叶子切片的切分结束偏移位置
            'l_t_title_row_id': Integer(),                 # 表格标题行号
            'l_t_start_row_id': Integer(),                 # 表格开始行号
            'l_t_end_row_id': Integer()                    # 表格结束行号
        }
    )

    class Index:
        name = settings.elasticsearch.index_paragraph_slice   # 定义索引名称
        settings = settings.elasticsearch.index_settings.model_dump()

    @classmethod
    def from_schema(cls, paragraph_slice: DocParagraphSchema, file_uuid: str = "") -> 'ESParagraphSlice':
        leaf_properties = dict()
        if paragraph_slice.leaf:
            leaf_properties = dict(
                l_idx=paragraph_slice.leaf_properties.l_idx,
                l_num=paragraph_slice.leaf_properties.l_num,
                l_p_start=paragraph_slice.leaf_properties.l_p_start,
                l_p_end=paragraph_slice.leaf_properties.l_p_end,
                l_t_title_row_id=paragraph_slice.leaf_properties.l_t_title_row_id,
                l_t_start_row_id=paragraph_slice.leaf_properties.l_t_start_row_id,
                l_t_end_row_id=paragraph_slice.leaf_properties.l_t_end_row_id
            )
        return cls(
            file_uuid=file_uuid,
            uuid=paragraph_slice.uuid,
            origin_slice_uuid=paragraph_slice.origin_slice_uuid,
            type=paragraph_slice.type,
            embed_text=paragraph_slice.embed_text,
            parent_uuid=paragraph_slice.parent_uuid,
            children_uuids=paragraph_slice.children_uuids,
            tree_token_length=paragraph_slice.tree_token_length,
            token_length=paragraph_slice.token_length,
            level=paragraph_slice.level,
            leaf=paragraph_slice.leaf,
            leaf_properties=leaf_properties,
            embedding=paragraph_slice.embedding,
            created_at=datetime.now(),
        )

    def to_schema(self) -> DocParagraphSchema:
        # 需要根据ESParagraphSlice的字段来构造DocParagraphSchema
        leaf_properties = None
        if self.leaf:
            leaf_properties = DocParagraphSchema.LeafProperties(
                l_idx=self.leaf_properties.l_idx,
                l_num=self.leaf_properties.l_num,
                l_p_start=self.leaf_properties.l_p_start,
                l_p_end=self.leaf_properties.l_p_end,
                l_t_title_row_id=self.leaf_properties.l_t_title_row_id,
                l_t_start_row_id=self.leaf_properties.l_t_start_row_id,
                l_t_end_row_id=self.leaf_properties.l_t_end_row_id
            )

        return DocParagraphSchema(
            file_uuid=self.file_uuid,
            uuid=self.uuid,
            type=self.type,
            origin_slice_uuid=self.origin_slice_uuid,
            embed_text=self.embed_text,
            parent_uuid=self.parent_uuid,
            children_uuids=self.children_uuids,
            tree_token_length=self.tree_token_length,
            token_length=self.token_length,
            level=self.level,
            leaf=self.leaf,
            leaf_properties=leaf_properties,
            embedding=self.embedding,
        )

    @classmethod
    def keys(cls, exclude=[]):
        keys = set(cls._doc_type.mapping.properties.properties.keys())
        return list(keys - set(exclude))


def initial_tables():
    ESFile.init()
    ESOriginSlice.init()
    ESParagraphSlice.init()
    ESTableRowSlice.init()
