import logging
import traceback
import pypeln as pl
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Document

from app.exceptions.http.doc import UploadFileInfoException
from app.schemas.doc import DocOriginSchema, FileMetaSchema
from app.schemas.elasticsearch import ESOriginSlice, ESFile
from app.services.doc.workflow_parse.schemas import Context
from app.support.helper import batch_generator, log_duration
from app.providers.elasticsearch_provider import get_es_client
from config.config import settings


@log_duration()
def upload_file_info(context: Context):
    try:
        upload_origin_slices(context.origin_slices, context.file_uuid)
        upload_file_meta(context.file_meta)
    except Exception as e:
        logging.error(f'upload_file_info error: {e}, {traceback.format_exc()}')
        raise UploadFileInfoException()


@log_duration(prefix="upload_file_info_")
def upload_origin_slices(origin_slices: list[DocOriginSchema], file_uuid: str):

    def _insert_es(_origin_slices: list[DocOriginSchema]):
        es_origin_slices = [ESOriginSlice.from_schema(origin_slice, file_uuid=file_uuid) for origin_slice in _origin_slices]
        if not bulk_create_documents(es_origin_slices):
            raise Exception("bulk_create_table_slices error")

    batch_generator(origin_slices, settings.app.wf_parse.insert_es_batch_size) | pl.thread.map(_insert_es, workers=settings.app.wf_parse.insert_es_concurrency) | list


def upload_file_meta(file_meta: FileMetaSchema):
    if not ESFile.from_schema(file_meta).save():
        raise Exception("upload_file_meta error")


def bulk_create_documents(documents: list[Document]) -> bool:
    success, _ = bulk(get_es_client(), [
        doc.to_dict(include_meta=True) for doc in documents
    ])
    return success == len(documents)
