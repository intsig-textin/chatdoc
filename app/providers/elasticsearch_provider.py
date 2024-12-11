

from fastapi import FastAPI
from elasticsearch import Elasticsearch
from elasticsearch_dsl import connections
# from app.schemas.elasticsearch import initial_tables
from config.config import settings


def register(app: FastAPI):
    es_dsl_connection = create_es_client()
    connections.add_connection('default', es_dsl_connection)
    # initial_tables()


def create_es_client() -> Elasticsearch:
    """
    创建一个 Elasticsearch 客户端。
    """
    es_client = Elasticsearch(
        hosts=settings.elasticsearch.hosts,
        http_auth=(settings.elasticsearch.username, settings.elasticsearch.password),
        timeout=settings.elasticsearch.conn_timeout,  # 设置超时
        max_retries=settings.elasticsearch.conn_max_retries,  # 设置重试次数
        retry_on_timeout=True  # 超时时重试
    )
    return es_client


def get_es_client() -> Elasticsearch:
    return connections.get_connection('default')


def cleanup(app: FastAPI):
    """
    关闭 Elasticsearch 客户端连接。
    """
    es_client = get_es_client()
    if es_client:
        es_client.close()
