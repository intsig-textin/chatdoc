import io
from minio import Minio, S3Error

# from aiobotocore.session import get_session
from app.exceptions.http.minio import MinioFileNotFoundException, MinioFileDownloadErrorException
from config.config import settings


class MinioClient(object):
    _client: Minio = None

    def __init__(self) -> None:
        self._bucket_name = settings.minio.bucket_name
        if not MinioClient._client:
            MinioClient._client = self.make_client()
        self._client = MinioClient._client

    @classmethod
    def make_client(cls) -> Minio:
        # 初始化 Minio 客户端
        return Minio(
            settings.minio.endpoint,
            access_key=settings.minio.access_key,
            secret_key=settings.minio.secret_key,
            secure=settings.minio.user_ssl,  # 如果是 HTTPS，设置为 True
        )

    # 上传文件
    def upload_content(self, object_name, content: bytes):
        try:
            self._client.put_object(self._bucket_name, object_name, data=io.BytesIO(content), length=len(content))
        except S3Error as e:
            raise e

    def download_content(self, object_name):
        try:
            self._client.get_object(self._bucket_name, object_name)
        except S3Error as e:
            raise e

    async def get_file(self, object_name):
        """
        获取文件流和元数据
        """
        try:
            obj = self._client.get_object(self._bucket_name, object_name)
            stat = self._client.stat_object(self._bucket_name, object_name)
            file_meta = {
                "filename": object_name.split("/")[-1],
                "content_type": stat.content_type,
                "size": stat.size,
            }
            return obj.stream(1024 * 1024), file_meta  # 以流形式返回
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise MinioFileNotFoundException()
            raise MinioFileDownloadErrorException(e.message)

        except Exception as e:
            raise MinioFileDownloadErrorException(e.message)
