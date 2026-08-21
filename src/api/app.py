from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.schemas.envelope import ErrorDetail


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="TCG Market Intelligence API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Include routers under /api/v1
    from src.api.routers.auth import router as auth_router
    from src.api.routers.cards import router as cards_router
    from src.api.routers.collect import router as collect_router
    from src.api.routers.collection import router as collection_router
    from src.api.routers.decks import router as decks_router
    from src.api.routers.exchange_rates import router as exchange_rates_router
    from src.api.routers.market import router as market_router
    from src.api.routers.scans import router as scans_router
    from src.api.routers.sets import router as sets_router

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(cards_router, prefix="/api/v1")
    app.include_router(sets_router, prefix="/api/v1")
    app.include_router(market_router, prefix="/api/v1")
    app.include_router(collect_router, prefix="/api/v1")
    app.include_router(collection_router, prefix="/api/v1")
    app.include_router(decks_router, prefix="/api/v1")
    app.include_router(scans_router, prefix="/api/v1")
    app.include_router(exchange_rates_router, prefix="/api/v1")

    # Health check (outside /api/v1)
    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err["loc"]) if err.get("loc") else None
            errors.append(
                ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=err["msg"],
                    field=field,
                )
            )
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=422,
            content={
                "data": None,
                "meta": {"request_id": request_id},
                "errors": [e.model_dump() for e in errors],
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        error = ErrorDetail(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "data": None,
                "meta": {"request_id": request_id},
                "errors": [error.model_dump()],
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        import structlog

        log = structlog.get_logger()
        log.error("unhandled_exception", error=str(exc), exc_info=True)
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        error = ErrorDetail(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
        )
        return JSONResponse(
            status_code=500,
            content={
                "data": None,
                "meta": {"request_id": request_id},
                "errors": [error.model_dump()],
            },
        )

    return app


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the API server with Uvicorn."""
    import uvicorn

    uvicorn.run(
        "src.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=True,
    )
