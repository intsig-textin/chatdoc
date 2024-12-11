

import requests
from config.config import settings
from app.support.helper import retry_exponential_backoff


@retry_exponential_backoff()
def rerank_api(pairs, headers=None, if_softmax=0):
    json_text = {
        "input": pairs,
        "if_softmax": if_softmax
    }
    completion = requests.post(url=settings.api.rerank.url,
                               headers=headers,
                               json=json_text)
    completion.raise_for_status()
    return completion.json()["rerank_score"]
