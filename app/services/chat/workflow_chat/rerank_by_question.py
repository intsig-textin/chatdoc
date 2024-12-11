

import logging
import re
import traceback
from typing import Counter

import numpy as np
import concurrent
from collections import OrderedDict

from app.exceptions.http.chat import RerankQuestionException
from app.libs.rerank import rerank_api
from app.schemas.doc import DocParagraphSchema, DocTableRowSchema, DocParagraphMetaTreeSchema
from app.services.chat.workflow_chat.schemas import Context, RetrieveContext
from app.support.helper import duplicates_list, log_duration, softmax, split_list


@log_duration()
def rerank_by_question(context: Context) -> list[RetrieveContext]:
    try:
        table_r_texts = ["".join(table_r.keywords) for table_r in context.table_retrieve_results]
        paragraph_r_texts = [paragraph_r.embed_text for paragraph_r in context.paragraph_retrieve_results]

        rerank_texts = [[strip_text_before_rerank(text)] for text in table_r_texts + paragraph_r_texts]
        # 调用 RerankApi 去获取分数
        rerank_scores = rerank_max_score(context.question_analysis.rewrite_question, rerank_texts)
        # 重排去重后去计算 repeat score
        r_contexts = generate_retrieve_contexts(context, rerank_scores)
        r_contexts.sort(key=lambda x: x.question_rerank_score, reverse=True)

        # Duplicat Remove【origin_slice有交集的进行重复计数】
        r_contexts = replace_duplicate_context(r_contexts)

        # 计算repeat的分数
        counter = Counter(r_contexts)
        for r_context, score in zip(list(counter.keys()), softmax(list(counter.values()))):
            r_context.repeat_score = score

        r_contexts = duplicates_list(r_contexts)
        # 计算粗排前的rank分数
        for r_context in r_contexts:
            # 求平均分
            r_context: RetrieveContext
            if isinstance(r_context.origin, DocTableRowSchema):
                r_context.retrieve_rank_score = 1 / (1 + context.table_retrieve_results.index(r_context.origin))
            elif isinstance(r_context.origin, DocParagraphSchema):
                r_context.retrieve_rank_score = 1 / (1 + context.paragraph_retrieve_results.index(r_context.origin))

        # 求平均分
        tt_rerank_score = sum([cur.question_rerank_score for cur in r_contexts]) if r_contexts else 0
        tt_retrieve_rank_score = sum([cur.retrieve_rank_score for cur in r_contexts]) if r_contexts else 0
        for r_context in r_contexts:
            r_context: RetrieveContext
            r_context.rerank_score_before_llm = (r_context.question_rerank_score / tt_rerank_score
                                                 + r_context.repeat_score
                                                 + r_context.retrieve_rank_score / tt_retrieve_rank_score
                                                 ) / 3
        return r_contexts
    except Exception as e:
        logging.error(f'rerank_by_question error: {e}, {traceback.format_exc()}')
        raise RerankQuestionException()


def generate_retrieve_contexts(context: Context, rerank_scores: list[float]) -> list[RetrieveContext]:
    def _get_tree_slices(node: DocParagraphMetaTreeSchema):
        node_slice = context.origin_slice_map[node.origin_slice_uuid]
        slices = [node_slice]
        for child in node.children:
            slices.extend(_get_tree_slices(child))
        return slices

    r_contexts = []
    for retrieval, rerank_score in zip(context.table_retrieve_results + context.paragraph_retrieve_results, rerank_scores):
        origin_slice = context.origin_slice_map[retrieval.origin_slice_uuid]
        if isinstance(retrieval, DocTableRowSchema):
            r_context = RetrieveContext(
                origin=retrieval,
                question_rerank_score=rerank_score,
                retrieval_type="table",
                origin_slice=origin_slice,
                tree_slices=[origin_slice],
            )
            r_contexts.append(r_context)

        elif isinstance(retrieval, DocParagraphSchema):
            r_context = RetrieveContext(
                origin=retrieval,
                question_rerank_score=rerank_score,
                retrieval_type="paragraph",
                origin_slice=origin_slice,
                tree_slices=_get_tree_slices(context.paragraph_meta_tree_map[retrieval.uuid]),
            )
            r_contexts.append(r_context)

    return r_contexts


def strip_text_before_rerank(str):
    """
    过滤字符开始的章节信息.
    Args:
        str:
    Returns:
    """
    pattern = (
        r'第[一二三四五六七八九十0123456789]+节|'
        r'第[一二三四五六七八九十0123456789]+章|'
        r'第[1234567890一二三四五六七八九十]+条|'
        r'[一二三四五六七八九十]+( |、|\.|\t|\s+|:|：|．)|'
        r'(\(|（)[一二三四五六七八九十]+(\)|）)|'
        r'[0-9]+(\t| |、|\s+)|'
        r'\d+(\.|．|\-)\d+(?=[^(\.|．|\-)+\d]+)|'
        r'\d+(\.|．)+(\t| |、|[\u4e00-\u9fa5]|\s+)|'
        r'(\(|（)[0-9]+(\)|）)|'
        r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]+'
    )
    new_str = re.sub(pattern, "", str)
    new_str = new_str.replace('|', ' ')
    return new_str


def rerank_max_score(txt1: str, txt2s) -> list[float]:
    """
    滑窗段落根据段落切分，算问题和召回内容的相似度.
    Args:
        txt1: 答案
        txt2s: 召回内容

    Returns:
        相似度打分
    """
    similarities = []
    txt2_combines_all = []
    txt2_combines_length = []
    for txt2 in txt2s:
        if isinstance(txt2, list):
            # 召回是增强切片的list
            txt2_combines_all.extend(txt2)
            txt2_combines_length.append(len(txt2))
        else:
            txt2_combines_all.append(txt2)
            txt2_combines_length.append(1)
    # 每个划窗的span的分数
    if len(txt2_combines_all) > 0:
        clean_txt2s = []
        for txt2 in txt2_combines_all:
            # 表格线替换为空
            txt2 = txt2.replace('|', ' ')
            clean_txt2s.append(txt2)
        concurrent_split_txts = split_list(txt2_combines_all, chunk_size=16)
        pairs = [[[txt1], concurrent_split_txt] for concurrent_split_txt in concurrent_split_txts]
        tasks_with_index = [
            (i, txt2) for i, txt2 in enumerate(pairs)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(rerank_api, txt2, if_softmax=0): idx for idx, txt2 in tasks_with_index}

            # 使用OrderedDict来保证按原顺序收集结果
            ordered_results = OrderedDict()
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                result = future.result()
                ordered_results[idx] = result

            # 提取并排序结果
            ress = [ordered_results[i] for i in range(len(ordered_results))]
        text_span_scores = [score for text_span_score in ress for score in text_span_score]
        text_span_scores = [round(score, 4) for score in softmax(text_span_scores)]

        start = 0
        for txt2_combine_length in txt2_combines_length:
            text_span_score = text_span_scores[start:start + txt2_combine_length]
            start += txt2_combine_length
            similarity = max(text_span_score) if text_span_score else 0  # txt2 为空列表的时候
            similarities.append(similarity)
    return np.array(similarities).tolist()


def replace_duplicate_context(contexts: list[RetrieveContext]) -> list[RetrieveContext]:
    """
    位置信息有重复的，取得分高的位置信息(排序top的), 仅替换，而并非删除
    """
    for i in range(0, len(contexts)):
        for j in range(i + 1, len(contexts)):
            if contexts[j].intersect(contexts[i]):
                # 添加 进 related
                contexts[j] = contexts[i]
                break

    return contexts
