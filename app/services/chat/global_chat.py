
from app.exceptions.http.global_chat import NonFileExistsException
from app.schemas.chat import GlobalChatRequest, GlobalChatResponse
from app.schemas.elasticsearch import ESFile
from app.services.chat.workflow_global_chat.run import run_workflow


class GlobalChatService:

    @staticmethod
    def validate_chat_params(chat_request: GlobalChatRequest):
        file_cnt = ESFile.search().count()
        if file_cnt == 0:
            raise NonFileExistsException()

    def chat(self, chat_request: GlobalChatRequest) -> GlobalChatResponse:
        self.validate_chat_params(chat_request)
        chat_resp = run_workflow(chat_request)
        if chat_request.stream:
            return GlobalChatResponse.create_stream_response(chat_resp)
        else:
            return chat_resp


global_chat_service = GlobalChatService()
