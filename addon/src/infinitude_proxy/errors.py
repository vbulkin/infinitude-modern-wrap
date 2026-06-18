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

import logging

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.requests import Request

from .parser import SouthboundParseError

logger = logging.getLogger(__name__)

# Status → stable machine-readable code. Covers the responses actually
# referenced in design/openapi.yaml plus a few common neighbors; anything
# outside this map falls through to `http_{status}`.
_STATUS_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    500: "internal_error",
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


async def southbound_parse_error_handler(
    request: Request, exc: SouthboundParseError
) -> Response:
    """A southbound body failed to parse — expected adversarial/garbage
    input, not a server bug.

    The thermostat firmware retries hard on 5xx, and a 500 on the
    high-frequency status path desyncs the directive channel (the same
    retry-storm `_try_persist` was written to avoid). So we discard the
    bad body and return a benign empty 200; the next well-formed POST
    self-heals. Logged at WARNING (not as a traceback) because malformed
    input is something to observe, not a crash to debug.

    The status path catches this in-handler and returns a proper
    directive instead, so this handler only fires for the other
    southbound POSTs (boot config, idu/odu config + status, energy,
    equipment events, metadata fallback) — all of which answer a bare
    200 in the happy path anyway.
    """
    logger.warning(
        "southbound parse failed path=%s: %s — discarding, returning 200",
        request.url.path, exc,
    )
    return Response(status_code=200)


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> Response:
    """True catch-all for unexpected errors no other handler claimed.

    * **Northbound** (`/v1/...`) — return the spec `Error` envelope with
      a 500 so API clients get a typed body instead of a bare Starlette
      HTML 500.
    * **Southbound** (everything not under `/v1`) — still shield the
      thermostat with a 200 so a server-side bug can't trigger a retry
      storm, but unlike a parse error this is a genuine fault, so it is
      logged with a full traceback (ServerErrorMiddleware re-raises after
      we respond) for diagnosis.

    `HTTPException` (incl. the 413 body-size reject) and
    `SouthboundParseError` are handled by their own handlers, so
    intentional status codes and expected parse failures don't land here.
    """
    path = request.url.path
    if not path.startswith("/v1"):
        logger.exception("southbound handler error on %s %s", request.method, path)
        return Response(status_code=200)
    logger.exception("unhandled error on %s %s", request.method, path)
    return JSONResponse(
        status_code=500,
        content=_error_body("internal_error", "internal server error"),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach all handlers — called once from create_app()."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
    app.add_exception_handler(
        SouthboundParseError, southbound_parse_error_handler
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
