import httpx
import requests
from config.config import settings


class TextinDownload(object):
    def __init__(self, app_id: str = None, app_secret: str = None):
        self._app_id = app_id or settings.api.pdf2md.app_id
        self._app_secret = app_secret or settings.api.pdf2md.app_secret
        self.url = settings.api.pdf2md.download_url

    def download_textin_img(self, image_id: str):
        headers = {
            'x-ti-app-id': self._app_id,
            'x-ti-secret-code': self._app_secret
        }
        res = requests.get(f'{self.url}?image_id={image_id}', data={'image_id': image_id} , headers=headers)
        res.raise_for_status()
        return res.json()['data']['image']

    async def aysnc_download_textin_img(self, image_id: str):
        headers = {
            'x-ti-app-id': self._app_id,
            'x-ti-secret-code': self._app_secret
        }

        async with httpx.AsyncClient() as client:
            # 异步发送 POST 请求
            response = await client.get(f'{self.url}?image_id={image_id}', data={'image_id': image_id} , headers=headers)

        return response.json()['data']['image']
