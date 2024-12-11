
from pydantic import BaseModel

from app.schemas.doc import CatalogTreeSchema, DocOriginSchema, DocParagraphSchema, DocTableRowSchema, FileMetaSchema, Pdf2MdSchema


class Context(BaseModel):
    file_uuid: str = ""                                     # 文件唯一标识
    pdf2md_result : Pdf2MdSchema = None                     # pdf2md解析结果
    catalog_tree: CatalogTreeSchema = None                  # 目录树
    origin_slices: list[DocOriginSchema] = []               # 文档原文信息
    table_row_slices: list[DocTableRowSchema] = []          # 文档原文信息
    paragraph_slices: list[DocParagraphSchema] = []         # 文档原文信息
    file_meta: FileMetaSchema = None                        # 文件元数据
