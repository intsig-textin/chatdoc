
import logging
from fastapi import UploadFile
import traceback

from app.exceptions.http.doc import Pdf2MdException
from app.libs.textin_ocr import TextinOcr
from app.schemas.doc import Pdf2MdSchema
from app.support import xjson
from app.support.helper import async_log_duration


@async_log_duration()
async def pdf2md(file: UploadFile) -> Pdf2MdSchema:
    try:
        file_content = file.read()
        response = await TextinOcr().aysnc_recognize_pdf2md(file_content)
        response.raise_for_status()
        response_dict = xjson.loads(response.content)
        if response_dict["code"] != 200:
            raise Exception(response_dict["code"])

        return Pdf2MdSchema.model_validate(response_dict)
    except Exception as e:
        logging.error(f'parse file error: {e}, {traceback.format_exc()}')
        raise Pdf2MdException()
