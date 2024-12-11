
import logging
import traceback
from app.exceptions.http.global_chat import GenerationException
from app.schemas.doc import FileMetaSchema, DocTableRowSchema
from app.services.chat.llm import LLM
from app.services.chat.workflow_global_chat.schemas import Context, RetrieveContext
from app.support.helper import group_by_func, log_duration
from app.consts.chat import QA_SYSTEM_V1, QA_USER_V1
from config.config import settings


@log_duration()
def generation(context: Context) -> list[RetrieveContext]:
    try:
        # 生成context
        _context = generate_context(context)
        llm_question = QA_USER_V1.format(question=context.question_analysis.rewrite_question, context=_context)
        return LLM().chat(QA_SYSTEM_V1, llm_question, context.chat_request.stream)

    except Exception as e:
        logging.error(f'generation error: {e}, {traceback.format_exc()}')
        raise GenerationException()


def generate_context(context: Context):
    """
    生成prompt
    """
    # 按照文件进行group
    max_length = settings.app.wf_global_chat.retrieval_max_length
    _context = ""

    file_uuid_mapper = {file.file_id: file for file in context.final_files}
    if 1 <= len(context.final_files) <= 10:
        each_length = max_length // len(context.final_files)
    else:
        each_length = max_length

    for _, (file_uuid, r_contexts) in enumerate(group_by_func(context.retrieve_contexts, lambda x: x.origin_slice.file_uuid)):
        file_meta: FileMetaSchema = file_uuid_mapper.get(file_uuid)
        _context += f"""# 来源文档
        - 文件名称：{file_meta.file_name}
        """
        each_contexts = ''
        for r_context in r_contexts:
            r_context: RetrieveContext
            r_llm_text = r_context.tree_text
            if isinstance(r_context.origin, DocTableRowSchema):
                # 表名 + 表内容
                each_contexts += r_context.origin.title + "：\n" + r_llm_text + "\n\n"
            else:
                # 标题 + 段落
                each_contexts += r_llm_text + "\n\n"
        _context += each_contexts[: each_length]

    return _context
