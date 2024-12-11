import os
from typing import Optional
import logging
import yaml

from pydantic_settings import BaseSettings as PydanticBaseSettings

CONFIG_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CONFIG_DIR_PATH)
CONFIG_YAML_PATH = os.environ.get("CONFIG_YAML_PATH")


class BaseSettings(PydanticBaseSettings):
    """
    基础配置类，所有配置类必须继承此类
    """

    def __init__(self, **kwargs):
        for field_name, field in self.model_fields.items():
            if isinstance(field.annotation, type) and issubclass(field.annotation, BaseSettings):
                if field_name not in kwargs or kwargs[field] is None:
                    kwargs[field_name] = field.annotation()

        super().__init__(**kwargs)


class ServerSettings(BaseSettings):
    app_name: str = "ChatDoc"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    env: str = "production"

    class Config:
        env_prefix = 'SERVER_'  # 设置环境变量前缀


class AppSettings(BaseSettings):
    class WorkflowChat(BaseSettings):
        rough_rank_score: float = 0.9   # 检索粗排的top-p
        retrieve_top_n: int = 15
        retrieval_max_length: int = 30000     # token最长限制
        rerank_score: float = 0.9       # 答案洗排的top-p

        class Config:
            env_prefix = 'APP_WF_CHAT_'  # 设置环境变量前缀

    class WorkflowGlobalChat(BaseSettings):
        rough_rank_score: float = 0.9   # 检索粗排的top-p
        retrieve_top_n: int = 15
        retrieval_max_length: int = 30000     # token最长限制
        rerank_score: float = 0.9       # 答案洗排的top-p

        class Config:
            env_prefix = 'APP_WF_GLOBAL_CHAT_'  # 设置环境变量前缀

    class WorkflowParse(BaseSettings):
        embedding_concurrency: int = 20
        embedding_batch_size: int = 32
        insert_es_concurrency: int = 20
        insert_es_batch_size: int = 3000
        insert_es_with_vector_batch_size: int = 300

        class Config:
            env_prefix = 'APP_WF_PARSE_'  # 设置环境变量前缀

    openapi_yaml_path: str = os.path.join(BASE_DIR, "docs/openapi/openapi.yaml")
    base_dir: str = BASE_DIR
    file_list_max_size: int = 10000       # 文件列表最多返回数量
    chat_max_file_count: int = 20         # 单次问答最大文件数量，默认值
    wf_parse: WorkflowParse
    wf_chat: WorkflowChat
    wf_global_chat: WorkflowGlobalChat

    class Config:
        env_prefix = 'APP_'  # 设置环境变量前缀


class LlmSettings(BaseSettings):
    class Qwen(BaseSettings):
        url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        model: str = "qwen-plus"
        api_key: str = "sk-XXX"
        max_token: int = 2000
        top_p: float = 0.9
        temperature: float = 0.1
        presence_penalty: float = 2.0
        enable_search: bool = False

        class Config:
            env_prefix = 'LLM_QWEN_'  # 设置环境变量前缀

    class Deepseek(BaseSettings):
        url: str = "https://api.deepseek.com"
        model: str = "deepseek-chat"
        api_key: str = "sk-XXX"
        max_token: int = 2000
        top_p: float = 0.9
        temperature: float = 0.1
        presence_penalty: float = 2.0

        class Config:
            env_prefix = 'LLM_DEEPSEEK_'  # 设置环境变量前缀

    class Gpt(BaseSettings):
        url: str = "https://api.openai.com/v1"
        model: str = "gpt-3.5-turbo"
        api_key: str = "sk-XXX"
        max_token: int = 2000
        top_p: float = 0.9
        temperature: float = 0.1
        presence_penalty: float = 2.0

        class Config:
            env_prefix = 'LLM_GPT_'  # 设置环境变量前缀

    llm: str = "qwen"           # 模型配置
    qwen: Qwen
    deepseek: Deepseek
    gpt: Gpt

    class Config:
        env_prefix = 'LLM_'  # 设置环境变量前缀


class LogSettings(BaseSettings):

    log_level : str = "INFO"
    log_retention: str = "14 days"
    app: Optional[AppSettings] = None

    @ property
    def log_path(self):
        if self.app:
            return self.app.base_dir + "/storages/logs/fastapi-{time:YYYY-MM-DD}.log"
        return BASE_DIR + "/storages/logs/fastapi-{time:YYYY-MM-DD}.log"

    class Config:
        env_prefix = 'LOG_'  # 设置环境变量前缀


class ApiSettings(BaseSettings):

    class Pdf2MdSettings(BaseSettings):
        url: str = "https://api.textin.com/ai/service/v1/pdf_to_markdown"
        download_url: str = "https://api.textin.com/ocr_image/download"
        app_id: str = "xxx_app_id"
        app_secret: str = "xxx_app_secret"
        options_dpi: int = 72
        options_page_start: int = 0
        options_page_count: int = 2000
        options_apply_document_tree: int = 1
        options_markdown_details: int = 1
        options_page_details: int = 1
        options_char_details: int = 1
        options_table_flavor: str = 'html'
        options_get_image: str = 'page'
        options_parse_mode: str = 'auto'

        class Config:
            env_prefix = 'API_PDF2MD_'  # 设置环境变量前缀

    class EmbeddingSettings(BaseSettings):
        url: str = "http://gpt-qa-embedding.ai.intsig.net/get_embedding"
        dimension: int = 1024
        digit: int = 8

        class Config:
            env_prefix = 'API_EMBEDDING_'  # 设置环境变量前缀

    class RerankSettings(BaseSettings):
        url: str = "http://gpt-qa-rerank.ai.intsig.net/rerank"

        class Config:
            env_prefix = 'API_RERANK_'  # 设置环境变量前缀

    pdf2md: Pdf2MdSettings
    embedding: EmbeddingSettings
    rerank: RerankSettings

    class Config:
        env_prefix = 'API_'  # 设置环境变量前缀


class ElasticSearchSettings(BaseSettings):

    class IndexSettings(BaseSettings):
        number_of_shards: int = 1
        number_of_replicas: int = 0
        refresh_interval: str = "200ms"

        class Config:
            env_prefix = 'ELASTICSEARCH_INDEX_SETTINGS_'  # 设置环境变量前缀

    hosts: str = "http://chatdoc-es-sandbox.ai.intsig.net:80"
    username: str = "elastic"
    password: str = "XXXXX"
    conn_timeout: int = 30
    conn_max_retries: int = 5
    index_file: str = "v1_file"
    index_origin_slice: str = "v1_origin_slice"
    index_table_row_slice: str = "v1_table_row_slice"
    index_paragraph_slice: str = "v1_paragraph_slice"
    index_settings: IndexSettings

    class Config:
        env_prefix = 'ELASTICSEARCH_'  # 设置环境变量前缀


class MinioSettings(BaseSettings):

    endpoint: str = "127.0.0.1:9000"
    access_key: str = "XXXX"
    secret_key: str = "XXXX"
    bucket_name: str = "chatdoc"
    user_ssl: bool = False

    class Config:
        env_prefix = 'MINIO_'  # 设置环境变量前缀


class MainSettings(BaseSettings):
    version: str
    server: ServerSettings
    app: AppSettings
    log: LogSettings
    api: ApiSettings
    elasticsearch: ElasticSearchSettings
    llm: LlmSettings
    minio: MinioSettings

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 这里可以在初始化后将 app 传递给 log
        self.log.app = self.app


def load_settings_from_yaml(file_path: str) -> MainSettings:
    with open(file_path, 'r') as file:
        yaml_content = yaml.safe_load(file)

    set_yaml_as_env_vars(yaml_content)
    settings = MainSettings()
    logging.info(f"Configs: {settings}")

    return settings


def set_yaml_as_env_vars(yaml_content: dict, parent_key: str = ''):
    """
    将 YAML 中的嵌套内容扁平化，并将其设置为环境变量
    """
    for key, value in yaml_content.items():
        # 如果是嵌套字典，则递归调用
        new_key = f"{parent_key}_{key}" if parent_key else key

        # 扁平化键名并设置为环境变量
        env_var_name = f"{new_key.upper()}"

        if isinstance(value, dict):
            # 如果是字典，递归设置嵌套值
            set_yaml_as_env_vars(value, new_key)
        elif value is not None and env_var_name not in os.environ:
            os.environ[env_var_name] = str(value)  # 环境变量中没有的才设置环境变量


def load_stopwords(file_dir_path: str) -> set:
    stopwords = set()
    # 遍历目录中的所有文件
    for filename in os.listdir(file_dir_path):
        file_path = os.path.join(file_dir_path, filename)
        # 仅处理文本文件
        if os.path.isfile(file_path) and filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stopwords.add(line.strip())  # 去除换行符和空格
    return stopwords


settings = load_settings_from_yaml(CONFIG_YAML_PATH or os.path.join(BASE_DIR, "config/config.yaml"))
stopwords = load_stopwords(os.path.join(CONFIG_DIR_PATH, "stopwords"))
