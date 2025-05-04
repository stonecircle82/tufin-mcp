import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
import structlog

# Get the configured structlog logger
logger = structlog.get_logger(__name__)

class RequestContextLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Clear context vars first
        structlog.contextvars.clear_contextvars()
        # Bind request_id and other request info to context vars
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            # Add user/API key info here later if possible from request
        )
        
        start_time = time.monotonic()
        response = None
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            status_code = response.status_code
        except Exception as exc:
            # Log unhandled exceptions before they propagate
            logger.exception("Unhandled exception during request processing")
            status_code = 500 # Internal Server Error
            raise exc # Re-raise the exception
        finally:
            end_time = time.monotonic()
            duration_ms = (end_time - start_time) * 1000
            
            # Log request completion
            log_event = logger.info if status_code < 400 else logger.warning
            log_event(
                "request_finished",
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                # Add response details if needed (e.g., content-length)
            )
            
            # Clear context vars after request is done
            structlog.contextvars.clear_contextvars()
            
        return response 