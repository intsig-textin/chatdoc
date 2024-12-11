import numpy as np
import heapq
from app.support.helper import log_duration, retry_exponential_backoff
from config.config import settings


@retry_exponential_backoff()
def acge_embedding(text, dimension=settings.api.embedding.dimension, digit=settings.api.embedding.digit):
    import requests

    json_text = {
        "input": [text],
        "matryoshka_dim": dimension,
        "digit": digit
    }

    completion = requests.post(url=settings.api.embedding.url, json=json_text)
    completion.raise_for_status()
    return completion.json()["embedding"][0]


@retry_exponential_backoff()
@log_duration(prefix="libs_")
def acge_embedding_multi(text_list, dimension=settings.api.embedding.dimension, digit=settings.api.embedding.digit, headers=None, url=None):
    import requests

    json_text = {
        "input": text_list,
        "matryoshka_dim": dimension,
        "digit": digit
    }
    completion = requests.post(url=url or settings.api.embedding.url,
                               headers=headers or None,
                               json=json_text)
    completion.raise_for_status()
    return completion.json()["embedding"]


def get_similar_top_n(texts: list[str], sentence: str, dimension=settings.api.embedding.dimension, top_n=1):
    '''
    给定一组文本和embedding_url，计算输入文本与每个文本的相似度，返回topN个文本
    '''
    if not texts:
        return []
    texts_vec = acge_embedding_multi(texts, dimension=dimension)
    sentence_embedding = acge_embedding(sentence, dimension=dimension)
    similarity_2d_list = (np.array([sentence_embedding]) @ np.array(texts_vec).T).tolist()

    if not similarity_2d_list:
        return []

    similarity_list = similarity_2d_list[0]
    topk_index = heapq.nlargest(top_n, range(len(similarity_list)), similarity_list.__getitem__)

    return [
        (texts[i], np.round(similarity_list[i], 4)) for i in topk_index
    ]
