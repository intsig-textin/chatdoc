
from typing import Generator, Union
from app.schemas.chat import GlobalChatRequest, ChatResponse
from app.services.chat.workflow_global_chat import analysis_question, locate_query_files, retrieve_small_global, retrieve_small
from app.services.chat.workflow_global_chat import small2big, update_origin_slice, rerank_by_question, truncation, generation, rerank_by_answer
from app.services.chat.workflow_global_chat.schemas import Context
from app.support.llm import generator_wrapper


def run_workflow(chat_request: GlobalChatRequest) -> Union[ChatResponse, Generator]:

    context = Context(chat_request=chat_request)
    context.question_analysis = analysis_question.analysis_question(context)
    context.query_locate_files = locate_query_files.locate_query_files(context)
    context.g_table_retrieve_results, context.g_paragraph_retrieve_results, context.global_locate_files = retrieve_small_global.retrieve_small_global(context)
    context.f_table_retrieve_results, context.f_paragraph_retrieve_results = retrieve_small.retrieve_small(context)
    context.table_retrieve_results = context.g_table_retrieve_results + context.f_table_retrieve_results
    context.paragraph_retrieve_results = context.g_paragraph_retrieve_results + context.f_paragraph_retrieve_results
    context.retrieve_contexts, context.final_files = rerank_by_question.rerank_by_question(context)
    context.origin_slice_map, context.paragraph_meta_tree_map = update_origin_slice.update_origin_slice(context)
    context.retrieve_contexts = small2big.small2big(context)
    context.retrieve_contexts = truncation.truncation(context)
    generation_resp = generation.generation(context)
    if chat_request.stream:
        generation_resp = process_generation_stream(context, generation_resp)
        return generation_resp
    else:
        context.llm_answer, total_tokens = generation_resp
        context.retrieve_contexts_by_answer = rerank_by_answer.rerank_by_answer(context)
        resp = ChatResponse(content=context.llm_answer, total_tokens=total_tokens, retrieval=[
            r.resp().model_dump() for r in context.retrieve_contexts_by_answer
        ])
        del context
        return resp


def process_generation_stream(context: Context, generation_resp: Generator[Union[str, int], None, None]):
    generation_resp = generator_wrapper(generation_resp)
    results = []
    for item in generation_resp:  # 假设 generation_resp 是异步生成器
        results.append(item)
        yield item  # 保持原有生成器行为
    context.llm_answer = results[-1].get("data", {}).get("content")
    context.retrieve_contexts_by_answer = rerank_by_answer.rerank_by_answer(context)
    yield dict(
        data=dict(
            retrieval=[
                r.resp().model_dump() for r in context.retrieve_contexts_by_answer
            ]
        )
    )
    del context
