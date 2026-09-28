import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.logging.context import sanitize_request_id, set_request_id

logger = logging.getLogger("app.middleware.request_tracing")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies defensive HTTP security headers to all responses.
    Prevents MIME-sniffing, clickjacking, and XSS without breaking
    React SPA routing, static asset serving, or Swagger/ReDoc API documentation.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # 1. Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 2. Clickjacking mitigation (SAMEORIGIN permits same-origin report & document previews)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # 3. Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 4. Content Security Policy (Practical, compatible with React, Vite dev, and Swagger UI)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' http: https: ws: wss:; "
            "frame-ancestors 'self';"
        )
        
        # 5. Cross-Site Scripting filter
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Correlates HTTP requests with an end-to-end Request ID.
    Propagates correlation ID to contextvars, logs, downstream processing, and response headers.
    Measures request processing duration in milliseconds.
    Catches unhandled server crashes to return a safe sanitized JSON error with X-Request-ID.
    """
    async def dispatch(self, request: Request, call_next):
        incoming_req_id = request.headers.get("X-Request-ID")
        req_id = sanitize_request_id(incoming_req_id)
        
        # Bind to contextvar and request.state
        set_request_id(req_id)
        request.state.request_id = req_id

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Attach correlation headers
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"

            # Emit structured HTTP access log
            logger.info(
                f"{request.method} {request.url.path} {response.status_code} in {duration_ms}ms",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "request_id": req_id,
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )
            return response

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled exception during {request.method} {request.url.path}: {str(exc)}",
                exc_info=True,
                extra={
                    "event": "unhandled_exception",
                    "request_id": req_id,
                    "path": request.url.path,
                    "method": request.method,
                    "duration_ms": duration_ms,
                    "error_type": type(exc).__name__,
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred. Quote the request ID for tracking.",
                    "request_id": req_id,
                },
                headers={"X-Request-ID": req_id, "X-Response-Time": f"{duration_ms}ms"},
            )
