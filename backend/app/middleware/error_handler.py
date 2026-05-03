import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:  # pragma: no cover
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "request_id": _request_id(request),
                "status_code": 500,
            },
        )


def register_exception_handlers(app):
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "detail": str(exc),
                "request_id": _request_id(request),
                "status_code": 400,
            },
        )
