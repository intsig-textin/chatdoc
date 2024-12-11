
import logging
import re
import traceback
import concurrent
from collections import OrderedDict

import numpy as np
from app.exceptions.http.chat import RerankAnswerException
from app.libs.rerank import rerank_api
from app.services.chat.workflow_chat.schemas import Context, RetrieveContext
from app.support.helper import log_duration, softmax, split_list
from config.config import settings


@log_duration()
def rerank_by_answer(context: Context) -> list[RetrieveContext]:
    try:
        return Reranking(context.retrieve_contexts)(question=context.question_analysis.rewrite_question, answer=context.llm_answer)
    except Exception as e:
        logging.error(f'rerank_by_answer error: {e}, {traceback.format_exc()}')
        raise RerankAnswerException()


class Reranking:
    """
    根据结果进行排序.
    """

    def __init__(self, retrieval_infos: list[RetrieveContext]):
        self.retrieval_infos = retrieval_infos

    @staticmethod
    def split_text_span(text, pattern):
        """表格切分， 按照\n切开，并过滤空串"""
        text_list_span = re.split(pattern, text)
        text_list_span = [item for item in text_list_span if item.strip()]
        return text_list_span

    @staticmethod
    def is_table_pipes(text):
        """判断字符串是否含有表格"""
        pattern = r'.*\|.*\|.*\|.*'  # 匹配含有三个以上的|并以|结束的模式
        if re.match(pattern, text):
            return True
        return False

    def rerank_score(self, txt1, txt2s):
        """两个文本的排序分数"""
        clean_txt2s = []
        for txt2 in txt2s:
            # 表格线替换为空
            txt2 = txt2.replace('|', ' ')
            clean_txt2s.append(txt2)
        pairs = [[txt1], clean_txt2s]
        scores = rerank_api(pairs, headers=None, if_softmax=0)
        return scores

    def rerank_max_score(self, txt1: str, txt2s) -> np.ndarray:
        """
        滑窗段落根据段落切分，算答案和召回内容的相似度.
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

            concurrent_split_txts = split_list(txt2_combines_all, chunk_size=16)
            tasks_with_index = [
                (i, txt2) for i, txt2 in enumerate(concurrent_split_txts)
            ]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(self.rerank_score, txt1, txt2): idx for idx, txt2 in tasks_with_index}

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

            # text_span_scores = self.rerank_score(txt1, txt2_combines_all)
            start = 0
            for txt2_combine_length in txt2_combines_length:
                text_span_score = text_span_scores[start:start + txt2_combine_length]
                start += txt2_combine_length
                similarity = max(text_span_score) if text_span_score else 0
                similarities.append(similarity)
        return np.array(similarities)

    def replace_info(self, answer):
        first_sentence = answer.split("，")[0]
        if "根据" in first_sentence:
            answer = answer.replace(first_sentence, '')
        return answer

    def jude_answer(self, question, answer):
        """
        根据答案来排序，若答案为空，则不排序；若答案太短，则把问题加上.
        Args:
            question: 原始问题
            answer: 回答答案
        Returns: 过滤后的答案.
        """
        re_answer = re.sub(r'[^\w\s]', '', answer)
        pattern = r'^(无|空|不知道|很抱歉)$'
        if re.match(pattern, re_answer):
            return None
        elif len(answer) <= 5:
            answer = question + " " + answer
            return answer
        else:
            return answer

    def __call__(self, question: str, answer: str, re_rank_score: float = settings.app.wf_chat.rerank_score):
        # 答案过滤
        answer = self.replace_info(answer)
        # 判断答案的三种类型
        answer = self.jude_answer(question=question, answer=answer)
        if answer is not None:
            # 取召回内容
            retrieval_texts = [retrieval_info.get_answer_rerank_texts() for retrieval_info in self.retrieval_infos]
            # _retrieval_texts = [retrieval_info.get_rerank_text_list() for retrieval_info in self.retrieval_infos]

            if len(retrieval_texts) == 1:
                self.retrieval_infos[0].answer_rerank_score = 1.0
            else:
                answer = answer[:350]
                ranking_scores = self.rerank_max_score(txt1=answer, txt2s=retrieval_texts)
                # else:
                #     ranking_scores = self.embedding_max_score(txt1=answer, txt2s=retrieval_texts)
                ranking_scores_norm = (ranking_scores / np.sum(ranking_scores)).tolist()
                for idx, retrieval_context in enumerate(self.retrieval_infos):
                    retrieval_context.answer_rerank_score = round(ranking_scores_norm[idx] * 0.7 + retrieval_context.rerank_score_before_llm * 0.3, 4)

        # 排序分数
        self.retrieval_infos = sorted(self.retrieval_infos, key=lambda x: x.answer_rerank_score, reverse=True)
        # top_p 的截断
        retrieval_infos = top_p(retrieval_infos=self.retrieval_infos, top_p_score=re_rank_score)
        return retrieval_infos


def top_p(retrieval_infos: list[RetrieveContext], top_p_score) -> list[RetrieveContext]:
    top_p_score_this, results = 0.0, []
    for retrieval_info in retrieval_infos:
        if top_p_score >= top_p_score_this:
            results.append(retrieval_info)
            top_p_score_this += retrieval_info.answer_rerank_score
        else:
            break
    return results
