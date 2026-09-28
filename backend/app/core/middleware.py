from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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
