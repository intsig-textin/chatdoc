from fastapi import FastAPI
from app.routes.api import api_router


def boot(app: FastAPI):
    # 注册api路由[routes/api.py]
    app.include_router(api_router, prefix="/api")

    # 打印路由
    if app.debug:
        for route in app.routes:
            print({'path': route.path, 'name': route.name, 'methods': route.methods})
