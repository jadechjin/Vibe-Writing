import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.websocket import websocket_router
from app.common.schemas import ApiResponse
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.realtime.broadcaster import TaskBroadcaster


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.broadcaster = TaskBroadcaster()
    yield
    app.state.broadcaster = None
    await asyncio.sleep(0)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse[dict](
                success=False,
                error=exc.message,
                data={"code": exc.code, "details": exc.details},
            ).model_dump(mode="json"),
        )

    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(websocket_router)
    return app


app = create_app()
