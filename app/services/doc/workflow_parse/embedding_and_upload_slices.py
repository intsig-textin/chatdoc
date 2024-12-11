
import logging
import traceback
import pypeln as pl
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Document

from app.exceptions.http.doc import EmbeddingUploadSlicesException
from app.schemas.doc import DocParagraphSchema, DocTableRowSchema, Pdf2MdSchema
from app.schemas.elasticsearch import ESParagraphSlice, ESTableRowSlice
from app.services.doc.workflow_parse.schemas import Context
from app.support.helper import batch_generator, log_duration
from app.providers.elasticsearch_provider import get_es_client
from app.libs.acge_embedding import acge_embedding_multi
from config.config import settings


@log_duration()
def embedding_and_upload_slices(context: Context) -> Pdf2MdSchema:
    try:
        upload_paragraph_slices(context.paragraph_slices, context.file_uuid)
        upload_table_slices(context.table_row_slices, context.file_uuid)
    except Exception as e:
        logging.error(f'embedding_and_upload_slices error: {e}, {traceback.format_exc()}')
        raise EmbeddingUploadSlicesException()


@log_duration(prefix="embedding_and_upload_slices_")
def upload_paragraph_slices(paragraph_slices: list[DocParagraphSchema], file_uuid: str):

    def _acge_embedding_multi(_paragraph_slices: list[DocParagraphSchema]):
        embeddings = acge_embedding_multi([x.embed_text for x in _paragraph_slices])
        for _paragraph_slice, embedding in zip(_paragraph_slices, embeddings):
            _paragraph_slice.embedding = embedding

        return _paragraph_slices

    def _insert_es(_paragraph_slices: list[DocParagraphSchema]):
        es_paragraph_slices = [ESParagraphSlice.from_schema(paragraph_slice, file_uuid=file_uuid) for paragraph_slice in _paragraph_slices]
        if not bulk_create_documents(es_paragraph_slices):
            raise Exception("bulk_create_paragraph_slices error")

        for _paragraph_slice in _paragraph_slices:
            del _paragraph_slice.embedding

        for _es_paragraph_slice in es_paragraph_slices:
            del _es_paragraph_slice.embedding

    batch_generator(
        (
            batch_generator(paragraph_slices, settings.app.wf_parse.embedding_batch_size)
            | pl.thread.map(
                _acge_embedding_multi,
                workers=settings.app.wf_parse.embedding_concurrency,
            )
            | pl.sync.flat_map(lambda x: x)
        ),
        settings.app.wf_parse.insert_es_with_vector_batch_size
    ) | pl.thread.map(_insert_es, workers=settings.app.wf_parse.insert_es_concurrency) | list


@log_duration(prefix="embedding_and_upload_slices_")
def upload_table_slices(table_slices: list[DocTableRowSchema], file_uuid: str):

    def _insert_es(_table_slices: list[DocTableRowSchema]):
        es_table_row_slices = [ESTableRowSlice.from_schema(table_slice, file_uuid=file_uuid) for table_slice in _table_slices]
        if not bulk_create_documents(es_table_row_slices):
            raise Exception("bulk_create_table_slices error")

    batch_generator(table_slices, settings.app.wf_parse.insert_es_batch_size) | pl.thread.map(_insert_es, workers=settings.app.wf_parse.insert_es_concurrency) | list


def bulk_create_documents(documents: list[Document]) -> bool:
    success, _ = bulk(get_es_client(), [
        doc.to_dict(include_meta=True) for doc in documents
    ])
    return success == len(documents)
