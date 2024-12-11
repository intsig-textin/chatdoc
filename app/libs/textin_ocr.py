from types import CoroutineType
import httpx
import requests
from config.config import settings


class TextinOcr(object):
    def __init__(self, app_id: str = None, app_secret: str = None):
        self._app_id = app_id or settings.api.pdf2md.app_id
        self._app_secret = app_secret or settings.api.pdf2md.app_secret
        self.url = settings.api.pdf2md.url

    @property
    def options(self):
        return {
            'dpi': settings.api.pdf2md.options_dpi,  # 使用 settings.api.pdf2md 配置项
            'page_start': settings.api.pdf2md.options_page_start,
            'page_count': settings.api.pdf2md.options_page_count,
            'apply_document_tree': settings.api.pdf2md.options_apply_document_tree,
            'markdown_details': settings.api.pdf2md.options_markdown_details,
            'page_details': settings.api.pdf2md.options_page_details,
            'char_details': settings.api.pdf2md.options_char_details,
            'table_flavor': settings.api.pdf2md.options_table_flavor,
            'get_image': settings.api.pdf2md.options_get_image,
            'parse_mode': settings.api.pdf2md.options_parse_mode,
        }

    def recognize_pdf2md(self, content):
        """
        pdf to markdown
        :param options: request params
        :param image: file bytes
        :return: response

        options = {
            'pdf_pwd': None,
            'dpi': 72,
            'page_start': 0,
            'page_count': 24,
            'apply_document_tree': 0,
            'markdown_details': 1,
            'page_details': 1,
            'table_flavor': 'md',
            'get_image': 'none',
            'parse_mode': 'auto',
        }

        """

        headers = {
            'x-ti-app-id': self._app_id,
            'x-ti-secret-code': self._app_secret
        }

        return requests.post(self.url, data=content, headers=headers, params=self.options)

    async def aysnc_recognize_pdf2md(self, content):
        headers = {
            'x-ti-app-id': self._app_id,
            'x-ti-secret-code': self._app_secret
        }

        if isinstance(content, CoroutineType):
            content = await content

        async with httpx.AsyncClient() as client:
            # 异步发送 POST 请求
            response = await client.post(self.url, data=content, headers=headers, params=self.options)

        return response
