

from app.libs.acge_embedding import acge_embedding
from app.providers.elasticsearch_provider import get_es_client
from app.schemas.chat import EmbeddingArgSchema
from app.support.rrf import RRF


def retrieval_embeddings(index, embedding_field_name, question_embedding: list[float], size: int, op_fields: list = [], must_conditions: list = []):
    """
    稠密检索，如向量匹配.
    Args:
        question_embedding: 查询问题的索引
        size: 返回的top-k的个数
        embedding_name: 查询问题匹配的ES数据库的表名的索引
    Returns:
    """
    source_string = """
                    double dp = dotProduct(params.queryVector, '{}');
                    if (dp < 0) {{
                        return 0;
                    }}
                    return dp;
                    """.format(embedding_field_name)

    must_conditions.append(
        {
            "script_score": {
                "query": {
                    "match_all": {}
                },
                "script": {
                    "source": source_string,
                    "params": {
                        "queryVector": question_embedding
                    }
                }
            }

        }
    )
    search_body = {
        "_source": op_fields,
        "size": size,
        "query": {
            "bool": {
                "must": must_conditions,
                "filter": [
                ]
            },
        }
    }

    resp = get_es_client().search(index=index, body=search_body)
    return [
        {
            "score": hit["_score"],
            "_id": hit["_id"],
            "_source": hit["_source"]
        }
        for hit in resp["hits"]["hits"]
    ]


def retrieve_bm25(index, text, text_field, size: int, op_fields: list = [], must_conditions: list = []):
    """
    稀疏检索,如bm25算法等.
    Args:
        size: 检索返回的个数
    Returns:
    """
    query = {
        "bool": {
            "should": [
                {
                    "match": {text_field: text},
                }
            ],
            "must": must_conditions,
        }
    }
    search_body = {
        "_source": op_fields,
        "size": size,
        "query": query,
    }
    resp = get_es_client().search(index=index, body=search_body)
    return [
        {
            "score": hit["_score"],
            "_id": hit["_id"],
            "_source": hit["_source"]
        }
        for hit in resp["hits"]["hits"]
    ]


def elasticsearch_retrieve(index, bm25_text, b25_text_field="embed_text", bm25_size=10, text_for_embedding="", op_fields=[], embedding_arg: EmbeddingArgSchema = None, must_conditions: list = None):
    """
    ES 召回方式
    如果传入embedding_args表明需要附加上 embedding的得分，使用rrf进行排名
    """

    def _filter_hit(_hit):
        embed_text = _hit["_source"]["embed_text"]
        # 去除根节点以及目录节点, 以及embed_text不为空
        return embed_text and embed_text != "Root" and "......." not in embed_text

    hits = []
    op_fields = list(set(op_fields) | {"_id"})
    must_conditions = must_conditions or []

    # BM25 Recall
    _hits = retrieve_bm25(index, bm25_text, b25_text_field, size=bm25_size, op_fields=op_fields, must_conditions=must_conditions)
    hits.extend(
        [dict(**_hit, retrieval_type="bm25") for _hit in _hits if _filter_hit(_hit)]
    )

    # Embedding Recall
    if embedding_arg:
        question_embedding = acge_embedding(text=text_for_embedding or bm25_text, dimension=embedding_arg.dimension)
        _hits = retrieval_embeddings(index, embedding_arg.field, question_embedding, embedding_arg.size, op_fields, must_conditions)
        hits.extend(
            [dict(**_hit, retrieval_type="acge") for _hit in _hits if _filter_hit(_hit)]
        )

    # k = 1 for test
    rerank_list = RRF().reciprocal_rank_fusion(hits, group_key="retrieval_type", k=1)
    results = [
        {
            "rrf_score": hit["score"],
            "id": hit["id"],
            **max(hit["results"], key=lambda x: x["score"]),
            "score": {cur['retrieval_type']: cur['score'] for cur in hit["results"]},
        }
        for hit in rerank_list
    ]

    return results
