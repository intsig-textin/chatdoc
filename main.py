from bootstrap.application import create_app
from config.config import settings
import uvicorn

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app="main:app", host=settings.server.host, port=settings.server.port, reload=False)
