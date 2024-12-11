

import logging
import re
import traceback

import numpy as np
import concurrent
from collections import OrderedDict

from app.exceptions.http.global_chat import RerankQuestionException
from app.libs.rerank import rerank_api
from app.schemas.doc import DocParagraphSchema, DocTableRowSchema, FileMetaSchema
from app.services.chat.workflow_global_chat.schemas import Context, RetrieveContext
from app.support.helper import duplicates_list, log_duration, sigmoid, softmax, split_list


@log_duration()
def rerank_by_question(context: Context) -> tuple[list[RetrieveContext], list[FileMetaSchema]]:
    try:
        table_r_texts = ["".join(table_r.keywords) for table_r in context.table_retrieve_results]
        paragraph_r_texts = [paragraph_r.embed_text for paragraph_r in context.paragraph_retrieve_results]

        rerank_texts = [[strip_text_before_rerank(text)] for text in table_r_texts + paragraph_r_texts]
        # 调用 RerankApi 去获取分数
        rerank_scores = rerank_max_score(context.question_analysis.rewrite_question, rerank_texts)
        # 使用file_name 去获取分数
        uuid_rerank_scores = rerank_score_by_filename(context.question_analysis.rewrite_question, context.query_locate_files, context.global_locate_files)
        # 生成召回切片
        r_contexts = generate_retrieve_contexts(context, rerank_scores, uuid_rerank_scores)
        r_contexts.sort(key=lambda x: x.rerank_score_before_llm, reverse=True)
        # 简单去重
        r_contexts = duplicates_list(r_contexts)
        # 根据分数过滤召回，如果过滤后超过5个，则使用过滤后的召回列表
        filter_r_contexts = [r for r in r_contexts if r.question_rerank_score >= 0.3]
        if len(filter_r_contexts) > 5:
            r_contexts = filter_r_contexts

        final_files = []
        for f in context.query_locate_files + context.global_locate_files:
            if f.file_id in set(r.origin.file_uuid for r in r_contexts) and f not in final_files:
                final_files.append(f)

        return r_contexts, final_files
    except Exception as e:
        logging.error(f'rerank_by_question error: {e}, {traceback.format_exc()}')
        raise RerankQuestionException()


def generate_retrieve_contexts(context: Context, rerank_scores: list[float], uuid_rerank_scores: dict[str, float]) -> list[RetrieveContext]:
    r_contexts = []
    for retrieval, rerank_score in zip(context.table_retrieve_results + context.paragraph_retrieve_results, rerank_scores):
        if retrieval.file_uuid not in uuid_rerank_scores:
            continue

        if isinstance(retrieval, DocTableRowSchema):
            # 下一Stage再去init这些slices
            r_context = RetrieveContext(
                origin=retrieval,
                question_rerank_score=rerank_score,
                filename_rerank_score=uuid_rerank_scores[retrieval.file_uuid],
                rerank_score_before_llm=rerank_score + uuid_rerank_scores[retrieval.file_uuid],
                retrieval_type="table",
            )
            r_contexts.append(r_context)

        elif isinstance(retrieval, DocParagraphSchema):
            r_context = RetrieveContext(
                origin=retrieval,
                question_rerank_score=rerank_score,
                filename_rerank_score=uuid_rerank_scores[retrieval.file_uuid],
                rerank_score_before_llm=rerank_score + uuid_rerank_scores[retrieval.file_uuid],
                retrieval_type="paragraph",
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


def rerank_score_by_filename(query: str, query_location_files: list[FileMetaSchema], global_locate_files: list[FileMetaSchema]):
    """
    算问题和召回文档标题的相似度.
    Returns:
        {file_uuid1: score1, file_uuid2: score2, ...}
    """
    name_uuid_dic = {c.file_name: c.file_id for c in global_locate_files}
    file_names = list(name_uuid_dic.keys())
    concurrent_split_txts = split_list(file_names, chunk_size=16)
    pairs = [[[query], concurrent_split_txt] for concurrent_split_txt in concurrent_split_txts]
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
    text_span_scores = [sigmoid(score) for text_span_score in ress for score in text_span_score]
    # hard_code
    max_score = max(text_span_scores) if text_span_scores else 0
    if 0.1 <= max_score * 10 < 1:
        alp = 10
    elif 0.1 <= max_score * 100 < 1:
        alp = 100
    else:
        alp = 1
    text_span_scores = [score * alp for score in text_span_scores]
    name_score_dic = dict(zip(file_names, text_span_scores))
    uuid_score_dic = {name_uuid_dic[k]: v for k, v in name_score_dic.items()}
    for file_id in [l.file_id for l in query_location_files]:
        uuid_score_dic[file_id] = 1.0
    return uuid_score_dic
