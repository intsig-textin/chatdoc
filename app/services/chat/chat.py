
from app.exceptions.http.chat import EmptyFileIdsException, ExceedMaxFileCountException, InvalidFileIdException
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.doc import FileMetaSchema
from app.schemas.elasticsearch import ESFile
from app.services.chat.workflow_chat.run import run_workflow
from config.config import settings


class ChatService:

    @staticmethod
    def validate_chat_params(chat_request: ChatRequest) -> list[FileMetaSchema]:
        if not chat_request.file_ids:
            raise EmptyFileIdsException()

        if len(chat_request.file_ids) > settings.app.chat_max_file_count:
            raise ExceedMaxFileCountException()

        file_hits = ESFile.search().extra(size=settings.app.file_list_max_size).filter("terms", **{"uuid.keyword": chat_request.file_ids}).execute().hits
        file_hits_ids = [hit.uuid for hit in file_hits]
        if len(set(chat_request.file_ids)) != len(set(file_hits_ids)):
            raise InvalidFileIdException(list(set(chat_request.file_ids) - set(file_hits_ids)))

        return [file_hit.to_schema() for file_hit in file_hits]

    def chat(self, chat_request: ChatRequest) -> ChatResponse:
        file_meta_list = self.validate_chat_params(chat_request)
        chat_resp = run_workflow(chat_request, file_meta_list)
        if chat_request.stream:
            return ChatResponse.create_stream_response(chat_resp)
        else:
            return chat_resp


chat_service = ChatService()
