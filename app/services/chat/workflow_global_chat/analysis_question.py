
from datetime import datetime
import logging
import re
import traceback

from app.consts.chat import QUESTION_KEYWORD_MAPPER
from app.exceptions.http.global_chat import QuestionAnalysisException
from app.services.chat.workflow_global_chat.schemas import Context
from app.schemas.chat import QuestionAnalysisSchema
from app.support.helper import log_duration
from config.config import stopwords
import jieba


@log_duration()
def analysis_question(context: Context) -> QuestionAnalysisSchema:
    try:
        rewrite_question = replace_by_keywords_mapper(context.chat_request.question)
        keywords = extract_keywords(context.chat_request.question)
        years = extract_years(context.chat_request.question, keywords)
        return QuestionAnalysisSchema(
            rewrite_question=rewrite_question,
            keywords=keywords,
            years=years
        )
    except Exception as e:
        logging.error(f'analysis_question error: {e}, {traceback.format_exc()}')
        raise QuestionAnalysisException()


def replace_by_keywords_mapper(question: str) -> str:
    for k, v in QUESTION_KEYWORD_MAPPER.items():
        question = re.sub(k, v, question)

    return question


def extract_keywords(question: str) -> list[str]:
    words = jieba.cut(question)

    #  简单过滤长度为1的词, 去除停用词等
    keywords = [word for word in words if len(word) > 1 and word not in stopwords]
    return keywords


def extract_years(question: str, keywords: list[str]) -> list[str]:
    """
    将问题中的时间描述词汇转换为具体的年份或年份范围。将抽取出的年份信息转换为具体的年份。

    :param question: 用户问题
    :param extract_years: 提取的年份信息
    :return: 各时间描述对应的年份或年份范围
    """
    year_pattern = r'\d{4}|\d{2}年'
    years = set(re.sub(r'年', '', match) for match in re.findall(year_pattern, question))

    # 处理两位数年份，假设为21世纪
    years = {str(2000 + int(r)) if len(r) == 2 else r for r in years}

    # 处理文字描述的时间信息
    current_year = datetime.now().year
    query_periods = {
        str(y) for k, years in convert_time_periods_to_years(current_year).items() if k in question for y in years
    }

    # 处理 keywords 参数中的年份范围
    for keyword in keywords or []:
        keyword_years = re.findall(year_pattern, keyword)
        if keyword_years:
            if any(separator in keyword for separator in ("-", "至", "到")):
                min_year, max_year = sorted(int(y[-2:]) + 2000 if len(y) == 2 else int(y) for y in keyword_years)
                years.update(str(y) for y in range(min_year, max_year + 1))
            else:
                years.update(keyword_years)

    # 返回四位数年份，过滤未来年份
    final_years = {r for r in years.union(query_periods) if len(r) == 4 and int(r) < 2100}
    return sorted(final_years)


def convert_time_periods_to_years(current_year):
    """
    将时间描述词汇转换为具体的年份或年份范围。

    : param current_year: 当前年份，整数。
    : return: 各时间描述对应的年份或年份范围。
    """
    this_year = current_year
    next_year = current_year + 1
    after_next_year = current_year + 2
    past_years_default = 5  # 默认过去五年的定义

    periods = {
        "未来一年": [next_year],
        "未来两年": list(range(next_year, next_year + 2)),
        "未来三年": list(range(next_year, next_year + 3)),
        "未来四年": list(range(next_year, next_year + 4)),
        "未来五年": list(range(next_year, next_year + 5)),
        "过去几年": list(range(this_year - past_years_default, this_year)),
        "这几年": list(range(this_year - 4, this_year + 1)),  # 假设这几年指的是最近的三年
        "这两年": list(range(this_year - 4, this_year)),
        "近几年": list(range(this_year - 4, this_year + 1)),
        "近些年": list(range(this_year - 4, this_year + 1)),
        "近年": list(range(this_year - 4, this_year + 1)),
        "近两年": list(range(this_year - 4, this_year)),
        "近三年": list(range(this_year - 4, this_year + 1)),
        "前三年": list(range(this_year - 3, this_year)),
        "前两年": list(range(this_year - 2, this_year)),
        "今年": [this_year],
        "明年": [next_year],
        "后年": [after_next_year],
        "去年": [this_year - 1],
        "前年": [this_year - 2]
    }

    return periods
