from fastapi import File, UploadFile

from config.config import settings
from app.consts.doc import EXT_ALLOW_TYPES
from app.schemas.doc import FileDeleteResponse, FileMetaSchema
from app.schemas.elasticsearch import ESFile, ESOriginSlice, ESParagraphSlice, ESTableRowSlice
from app.services.doc.workflow_parse.run import run_workflow


class DocParserService:

    def __init__(self) -> None:
        pass

    @staticmethod
    def validate_file_type(file: UploadFile = File(...)) -> bool:
        # if file.content_type not in FASTAPI_ALLOW_TYPES:
        #     return False

        for ext in EXT_ALLOW_TYPES:
            if file.filename.endswith(ext):
                return True

        return False

    async def parse_file(self, file: UploadFile = File(...)) -> FileMetaSchema:
        return await run_workflow(file)

    async def get_all_files(self) -> list[FileMetaSchema]:
        es_files: list[ESFile] = ESFile.search().extra(size=settings.app.file_list_max_size).source(excludes=["paragraph_slices_meta", "extra"]).execute().hits
        return [es_file.to_schema() for es_file in es_files]

    async def delete_file(self, file_id: str) -> FileDeleteResponse:

        # 删除 ESParagraphSlice 中与文件关联的切片记录
        paragraph_slice_query = ESParagraphSlice.search().filter("term", **{"file_uuid.keyword": file_id})
        paragraph_slice_delete_count = paragraph_slice_query.delete().total

        # 删除 ESTableRowSlice 中与文件关联的切片记录
        table_slice_query = ESTableRowSlice.search().filter("term", **{"file_uuid.keyword": file_id})
        table_slice_delete_count = table_slice_query.delete().total

        # 删除 ESOriginSlice 中与文件关联的切片记录
        origin_slice_query = ESOriginSlice.search().filter("term", **{"file_uuid.keyword": file_id})
        origin_slice_delete_count = origin_slice_query.delete().total

        # 删除 ESFile 中的文件记录
        file_query = ESFile.search().filter("term", **{"uuid.keyword": file_id})
        file_delete_count = file_query.delete().total

        return FileDeleteResponse(
            file_delete_count=file_delete_count,
            origin_slice_delete_count=origin_slice_delete_count,
            table_slice_delete_count=table_slice_delete_count,
            paragraph_slice_delete_count=paragraph_slice_delete_count
        )


doc_parse_service_ins = DocParserService()
