"""Spec-compliant error envelope — `{ "error": { "code", "message", "details"? } }`.

FastAPI's default 404/422 shape is `{"detail": ...}`; the openapi spec
declares `Error` as `{ error: { code, message, details[] } }`. These
handlers translate the defaults so clients see the shape documented in
the spec.

Code mapping is deliberately coarse — the machine-readable `code` field
is stable across minor releases; new statuses fall through to
`http_{status}` so unmapped cases are still well-typed.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.requests import Request

# Status → stable machine-readable code. Covers the responses actually
# referenced in design/openapi.yaml plus a few common neighbors; anything
# outside this map falls through to `http_{status}`.
_STATUS_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    502: "upstream_error",
    503: "upstream_unavailable",
    504: "upstream_timeout",
}


def _code_for(status: int) -> str:
    return _STATUS_CODE_MAP.get(status, f"http_{status}")


def _error_body(code: str, message: str, details=None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Translate `HTTPException(detail=...)` into the spec envelope.

    `detail` is usually a string; we echo it into `message`. If a caller
    hands us a dict shaped like the spec (`{"code": "...", "message":
    "...", "details": [...]}`) we pass it through — lets individual
    handlers supply a more specific `code` without plumbing a custom
    exception type.
    """
    code = _code_for(exc.status_code)
    message = ""
    details = None
    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code", code))
        message = str(exc.detail.get("message", ""))
        details = exc.detail.get("details")
    else:
        message = str(exc.detail) if exc.detail is not None else ""
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, message, details),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate pydantic `RequestValidationError` into `Error.details[]`.

    Each pydantic error becomes one detail row: `path` is a JSON-pointer-
    like `/body/activity`, `issue` is the human message. Matches the
    `ErrorDetail` schema in models.py.
    """
    details = [
        {"path": "/" + "/".join(str(p) for p in err.get("loc", ())),
         "issue": err.get("msg", "")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_body(
            "validation_error", "request body failed validation", details
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach both handlers — called once from create_app()."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
