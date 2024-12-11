import numpy as np
from itertools import groupby


class RRF():
    """
    https://github.com/Raudaschl/rag-fusion/tree/master
    RRF简介：https://zhuanlan.zhihu.com/p/664143375
    """

    def __init__(self):
        pass

    def softmax(self, x):
        if x == []:
            return 0
        e_x = np.exp(x - np.max(x))  # 防止指数溢出
        return e_x / np.sum(e_x)

    def reciprocal_rank_fusion(self, search_results, group_key="type", identity_key="_id", score_key="score", k=60):
        '''
        description: return id, fused_score, values
        return {*}
        '''
        fused_scores = {}

        def get_attr(x, key):
            return getattr(x, key) if hasattr(x, key) else x[key]

        for _, _type_results in groupby(sorted(search_results, key=lambda x: get_attr(x, group_key)), key=lambda x: get_attr(x, group_key)):
            for rank, _type_result in enumerate(_type_results):
                _id = get_attr(_type_result, identity_key)
                _ = get_attr(_type_result, score_key)
                if _id not in fused_scores:
                    fused_scores[_id] = 0
                fused_scores[_id] += 1 / (rank + k)

        _id_group_map = {k: list(v) for k, v in groupby(sorted(search_results, key=lambda x: get_attr(x, identity_key)), key=lambda x: get_attr(x, identity_key))}

        rerank_results = [dict(
            id=_id,
            score=fused_score,
            results=_id_group_map.get(_id)
        ) for _id, fused_score in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)]

        if rerank_results:
            for result, softmax_score in zip(rerank_results, self.softmax([x["score"] for x in rerank_results]).tolist()):
                result["score"] = softmax_score

        return rerank_results
