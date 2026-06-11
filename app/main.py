from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.carddav import CardDAVClient, ConflictError, NotFoundError, UpstreamError
from app.config import load_settings


def create_app() -> FastAPI:
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with httpx.AsyncClient(
            auth=(settings.baikal_user, settings.baikal_pass),
            timeout=10.0,
        ) as http:
            app.state.carddav = CardDAVClient(settings, http)
            yield

    app = FastAPI(title="CardDAV-REST", lifespan=lifespan)

    @app.middleware("http")
    async def require_api_key(request: Request, call_next):
        if request.url.path != "/health" and request.headers.get("X-API-Key") != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
        return await call_next(request)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(UpstreamError)
    async def upstream_handler(request: Request, exc: UpstreamError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
