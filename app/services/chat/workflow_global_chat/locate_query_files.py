
from difflib import get_close_matches
import logging
import traceback
from elasticsearch_dsl import Q

from app.exceptions.http.global_chat import LocateQueryFilesException
from app.schemas.doc import FileMetaSchema
from app.schemas.elasticsearch import ESFile
from app.services.chat.workflow_global_chat.schemas import Context
from app.support.helper import log_duration
from app.consts.chat import LOCATE_FILE_FILTER_WORDS


@log_duration()
def locate_query_files(context: Context) -> list[FileMetaSchema]:
    try:
        query_for_match = generate_match_word(context.question_analysis.rewrite_question)
        file_hits: list[ESFile] = ESFile.search().extra(
            _source=ESFile.keys_brief(),
            size=100
        ).query(Q("bool", should=[Q("match", filename=query_for_match)])).execute().hits
        to_match_file_names_mapper = {
            file_hit.filename.split(".")[0]: file_hit for file_hit in file_hits
        }
        to_match_file_names = set(to_match_file_names_mapper.keys()) | set([""])
        file_name_matches = []
        for keyword in context.question_analysis.keywords:
            file_name_matches.extend(get_close_matches(keyword, to_match_file_names, cutoff=0.3))

        file_name_matches = file_name_matches or get_close_matches(query_for_match, to_match_file_names, cutoff=0.3)
        file_name_matches = list(set(file_name_matches))
        location_files = [to_match_file_names_mapper[_match_file_name] for _match_file_name in file_name_matches if _match_file_name in to_match_file_names_mapper]
        return [_f.to_schema() for _f in location_files]

    except Exception as e:
        logging.error(f'analysis_question error: {e}, {traceback.format_exc()}')
        raise LocateQueryFilesException()


def generate_match_word(rw_question: str) -> str:
    for word in LOCATE_FILE_FILTER_WORDS:
        rw_question = rw_question.replace(word, "")
    return rw_question
