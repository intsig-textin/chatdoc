import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager


from app.providers import app_provider, logging_provider, route_provider, elasticsearch_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup(app, app_provider)
    yield  # 允许请求处理
    # 释放 Elasticsearch 资源等
    cleanup(app, elasticsearch_provider)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    register(app, logging_provider)
    register(app, app_provider)
    register(app, elasticsearch_provider)

    boot(app, route_provider)

    return app


def register(app, provider):
    provider.register(app)
    logging.info(provider.__name__ + ' registered')


def boot(app, provider):
    provider.boot(app)
    logging.info(provider.__name__ + ' booted')


def startup(app, provider):
    provider.startup(app)
    logging.info(provider.__name__ + ' startup')


def cleanup(app, provider):
    provider.cleanup(app)
    logging.info(provider.__name__ + ' cleanup')
