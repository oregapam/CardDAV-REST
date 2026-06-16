from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.carddav import CardDAVClient, ConflictError, NotFoundError, UpstreamError
from app.config import load_settings
from app.routers.contacts import router as contacts_router


def create_app() -> FastAPI:
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with httpx.AsyncClient(
            auth=httpx.DigestAuth(settings.baikal_user, settings.baikal_pass),
            timeout=10.0,
        ) as http:
            app.state.carddav = CardDAVClient(settings, http)
            app.state.name_format = settings.name_format
            app.state.default_region = settings.default_region
            app.state.required_fields = settings.required_fields
            yield

    app = FastAPI(title="CardDAV-REST", lifespan=lifespan)
    app.include_router(contacts_router)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["ApiKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                operation.setdefault("security", [{"ApiKeyAuth": []}])
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    @app.middleware("http")
    async def require_api_key(request: Request, call_next):
        public = {"/health", "/docs", "/redoc", "/openapi.json"}
        if request.url.path not in public and request.headers.get("X-API-Key") != settings.api_key:
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
