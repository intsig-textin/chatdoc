import logging
import traceback
from app.exceptions.http.chat import RetrieveSmallException
from config.config import settings
from app.libs.acge_embedding import get_similar_top_n
from app.schemas.elasticsearch import ESParagraphSlice, ESTableRowSlice
from app.services.chat.workflow_chat.schemas import Context
from app.services.elasticsearch_retrieval import elasticsearch_retrieve
from app.support.helper import log_duration
from app.schemas.doc import DocTableRowSchema, DocParagraphSchema
from app.schemas.chat import EmbeddingArgSchema


@log_duration()
def retrieve_small(context: Context) -> tuple[list[DocTableRowSchema], list[DocParagraphSchema]]:
    try:
        file_ids = [cur.file_id for cur in context.file_meta_list]
        table_retrieve_results = retrieve_by_table(context, file_ids)
        paragraph_retrieve_results = retrieve_by_paragraph(context, file_ids)
        return table_retrieve_results, paragraph_retrieve_results

    except Exception as e:
        logging.error(f'retrieve_small error: {e}, {traceback.format_exc()}')
        raise RetrieveSmallException()


def retrieve_by_table(context: Context, file_ids: list[str]) -> list[DocTableRowSchema]:
    # 表格召回
    table_retrieve_results = []
    for keyword in context.question_analysis.keywords:
        hits = elasticsearch_retrieve(
            index=ESTableRowSlice.Index.name,
            bm25_text=keyword,
            b25_text_field="embed_text",
            bm25_size=min(200, 5 * len(file_ids)),
            op_fields=ESTableRowSlice.keys(),
            must_conditions=[dict(terms={"file_uuid.keyword": file_ids})]
        )
        table_retrieve_results.extend(
            ESTableRowSlice.from_es(hit).to_schema() for hit in hits
        )

    table_retrieve_results = filter_by_embedding(table_retrieve_results, context.chat_request.question, 0.5)
    return table_retrieve_results[0:min(3 * len(file_ids), 100)]


def retrieve_by_paragraph(context: Context, file_ids: list[str]) -> list[DocParagraphSchema]:
    # 段落召回
    paragraph_retrieve_results = []

    size = min(300, 15 * len(file_ids))
    hits = elasticsearch_retrieve(
        index=ESParagraphSlice.Index.name,
        bm25_text=context.question_analysis.rewrite_question,
        bm25_size=size,
        b25_text_field="embed_text",
        op_fields=ESParagraphSlice.keys(exclude=["embedding"]),
        text_for_embedding=context.question_analysis.rewrite_question,
        embedding_arg=EmbeddingArgSchema(field="embedding", dimension=settings.api.embedding.dimension, size=size),
        must_conditions=[dict(terms={"file_uuid.keyword": file_ids})]
    )

    paragraph_retrieve_results = [
        ESParagraphSlice.from_es(hit).to_schema() for hit in hits
    ]

    return paragraph_retrieve_results[0:min(8 * len(file_ids), 150)]


def filter_by_embedding(hits: list[DocTableRowSchema], sentence: str, match_score: float):
    keywords = ["".join(hit.keywords) for hit in hits]
    embedding_matches = get_similar_top_n(texts=keywords, sentence=sentence, top_n=len(keywords))
    matches = [embedding_match for embedding_match in embedding_matches if embedding_match[1] >= match_score]
    return [hit for hit in hits if "".join(hit.keywords) in list([match[0] for match in matches])]
