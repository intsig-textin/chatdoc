from fastapi import UploadFile, File

from app.schemas.doc import DocParagraphMetaTreeSchema, FileMetaSchema
from app.services.doc.workflow_parse import catalog, pdf2md, gen_origin_slices, gen_table_slices, gen_paragraph_slices, embedding_and_upload_slices, upload_file_info, upload2minio
from app.services.doc.workflow_parse.schemas import Context
from app.support.helper import uuid_base62


async def run_workflow(file: UploadFile = File(...)) -> FileMetaSchema:

    context = Context(file_uuid=uuid_base62())
    file_meta = context.file_meta = FileMetaSchema(file_id=context.file_uuid, file_name=file.filename)
    context.pdf2md_result = await pdf2md.pdf2md(file)
    context.catalog_tree = catalog.catalog(context)
    context.origin_slices = gen_origin_slices.gen_origin_slices(context)
    context.table_row_slices = gen_table_slices.gen_table_slices(context)
    context.paragraph_slices = gen_paragraph_slices.gen_paragraph_slices(context)
    context.file_meta.paragraph_slices_meta = DocParagraphMetaTreeSchema.from_paragraphs(context.paragraph_slices)
    embedding_and_upload_slices.embedding_and_upload_slices(context)
    # 上传extra信息到minio中，如果不需要前端展示，注释此行即可
    context.file_meta.extra, context.file_meta.thumbnail = upload2minio.upload2minio(context)
    upload_file_info.upload_file_info(context)
    del context
    return file_meta
