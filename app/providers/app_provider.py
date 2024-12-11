import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import yaml
from config.config import settings


def register(app: FastAPI):
    app.debug = settings.server.debug
    app.title = settings.server.app_name
    add_global_middleware(app)


def add_global_middleware(app: FastAPI):
    """
    注册全局中间件
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time*1000:.1f}ms"
        return response


def startup(app: FastAPI):
    dump_openapi(app)


def dump_openapi(app: FastAPI):
    openapi_schema = app.openapi()
    openapi_schema["servers"] = [
        {
            "url": "https://api.example.com",
            "description": "Production server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
    app.openapi_schema = openapi_schema
    with open(settings.app.openapi_yaml_path, "w") as yaml_file:
        yaml.dump(app.openapi(), yaml_file, default_flow_style=False, allow_unicode=True)
