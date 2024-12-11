import logging
import traceback

from app.exceptions.http.global_chat import RetrieveSmallGlobalException
from app.libs.acge_embedding import get_similar_top_n
from app.schemas.elasticsearch import ESParagraphSlice, ESTableRowSlice
from app.services.chat.workflow_global_chat.schemas import Context
from app.services.elasticsearch_retrieval import elasticsearch_retrieve
from app.support.helper import log_duration
from app.schemas.doc import DocTableRowSchema, DocParagraphSchema, FileMetaSchema
from app.schemas.chat import EmbeddingArgSchema
from app.schemas.elasticsearch import ESFile

from config.config import settings


@log_duration()
def retrieve_small_global(context: Context) -> tuple[list[DocTableRowSchema], list[DocParagraphSchema], list[FileMetaSchema]]:
    try:
        table_retrieve_results = retrieve_by_table(context)
        paragraph_retrieve_results = retrieve_by_paragraph(context)
        global_locate_file_uuids = [_t.file_uuid for _t in table_retrieve_results] + [_p.file_uuid for _p in paragraph_retrieve_results]
        global_locate_file_uuids = list(set(global_locate_file_uuids))
        global_locate_files: list[ESFile] = ESFile.search().extra(
            _source=ESFile.keys_brief(),
            size=1.2 * len(global_locate_file_uuids)
        ).filter("terms", **{"uuid.keyword": global_locate_file_uuids}).execute().hits
        global_locate_files = [_f.to_schema() for _f in global_locate_files]
        return table_retrieve_results, paragraph_retrieve_results, global_locate_files

    except Exception as e:
        logging.error(f'retrieve_small_global error: {e}, {traceback.format_exc()}')
        raise RetrieveSmallGlobalException()


def retrieve_by_table(context: Context) -> list[DocTableRowSchema]:
    # 表格召回
    table_retrieve_results = []
    for keyword in context.question_analysis.keywords:
        hits = elasticsearch_retrieve(
            index=ESTableRowSlice.Index.name,
            bm25_text=keyword,
            b25_text_field="embed_text",
            bm25_size=25,
            op_fields=ESTableRowSlice.keys(),
        )
        table_retrieve_results.extend(
            ESTableRowSlice.from_es(hit).to_schema() for hit in hits
        )

    table_retrieve_results = filter_by_embedding(table_retrieve_results, context.chat_request.question, 0.5)
    return table_retrieve_results


def retrieve_by_paragraph(context: Context) -> list[DocParagraphSchema]:
    # 段落召回
    paragraph_retrieve_results = []

    hits = elasticsearch_retrieve(
        index=ESParagraphSlice.Index.name,
        bm25_text=context.question_analysis.rewrite_question,
        bm25_size=25,
        b25_text_field="embed_text",
        op_fields=ESParagraphSlice.keys(exclude=["embedding"]),
        text_for_embedding=context.question_analysis.rewrite_question,
        embedding_arg=EmbeddingArgSchema(field="embedding", dimension=settings.api.embedding.dimension, size=25),
    )

    paragraph_retrieve_results = [
        ESParagraphSlice.from_es(hit).to_schema() for hit in hits
    ]

    return paragraph_retrieve_results


def filter_by_embedding(hits: list[DocTableRowSchema], sentence: str, match_score: float):
    keywords = ["".join(hit.keywords) for hit in hits]
    embedding_matches = get_similar_top_n(texts=keywords, sentence=sentence, top_n=len(keywords))
    matches = [embedding_match for embedding_match in embedding_matches if embedding_match[1] >= match_score]
    return [hit for hit in hits if "".join(hit.keywords) in list([match[0] for match in matches])]
