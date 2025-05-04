import logging # Keep for basic config if needed, but structlog handles root
import uvicorn
from fastapi import FastAPI, Response, status, Request # Added Request
# Add necessary imports for security
from fastapi import Depends # Keep Depends if used elsewhere, otherwise remove
import structlog # Import structlog
from fastapi import HTTPException

# Rate Limiting Imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
# Import the limiter instance from its new location
from .core.limiter import limiter

# Import settings and Role enum
from .core.config import settings, UserRole # Relative import
# Import logging setup function
from .core.logging_config import setup_logging
# Import security dependencies from the new file
from .core.dependencies import get_authenticated_user, require_permission # Corrected import (removed require_role)
# Import the Tufin client and lifecycle functions
from .clients.tufin import TufinApiClient, get_tufin_client, create_tufin_client, close_tufin_client
# Import the secure store instance
from .core.secure_store import secure_store_instance
# Import the SecureChange router
from .api.v1.endpoints import securechange as securechange_router
# Import the SecureTrack router
from .api.v1.endpoints import securetrack as securetrack_router
# Import Middleware
from .middleware.request_context import RequestContextLogMiddleware

# --- Rate Limiter Setup --- 
# Moved to core/limiter.py

# --- Logging Setup ---
# Remove old basicConfig
# Call the setup function BEFORE creating the FastAPI app
setup_logging()

# Get a logger instance (now configured by structlog)
logger = structlog.get_logger(__name__)

# --- API Key Security --- 
# Moved to core/dependencies.py

# --- RBAC Dependency --- 
# Moved to core/dependencies.py

# --- FastAPI Lifespan Events --- 

async def startup_event():
    """Application startup logic: Create Tufin client and load dev API keys."""
    logger.info("Running application startup event...")
    await create_tufin_client()
    logger.info("Loading initial API keys for development (if configured)...")
    await secure_store_instance.load_initial_keys()

async def shutdown_event():
    """Application shutdown logic: Close Tufin client."""
    logger.info("Running application shutdown event...")
    await close_tufin_client()

# --- FastAPI Application ---
app = FastAPI(
    title="Tufin MCP Server",
    description="MCP Server providing a unified interface to Tufin SecureTrack and SecureChange APIs.",
    version="0.1.0",
    on_startup=[startup_event], # Register startup event
    on_shutdown=[shutdown_event] # Register shutdown event
)

# --- Add Rate Limiter State and Handler ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Middleware --- 
app.add_middleware(RequestContextLogMiddleware)

# --- API Endpoints / Routers ---

# Include SecureChange Router
app.include_router(
    securechange_router.router, 
    prefix="/api/v1", # Prefix for all SecureChange endpoints
    # tags=["SecureChange Tickets"] # Optionally re-define tag here or use the one in the router
)

# Include SecureTrack Router
app.include_router(
    securetrack_router.router, 
    prefix="/api/v1", 
    # tags=["SecureTrack"] # Optional tag override
)

@app.get("/health", tags=["Management"], status_code=status.HTTP_200_OK)
@limiter.exempt # Exempt health check from rate limiting
async def health_check():
    """
    Simple health check endpoint.
    Returns 200 OK if the server is running.
    """
    logger.info("Health check endpoint called")
    logger.info("Health check processed") # Use structlog logger
    return {"status": "ok"}

# Apply RBAC: Allow any authenticated user (any role defined)
@app.get("/secure", tags=["Test"], dependencies=[Depends(require_permission("access_secure_endpoint"))])
async def secure_endpoint():
    """
    An example endpoint protected by API key authentication.
    Requires any valid API key with an assigned role.
    """
    logger.info("Secure endpoint called successfully with valid API key and role.")
    return {"message": "You have accessed the secure endpoint!"}

# Apply RBAC: Allow only ADMIN role (using permission ID)
@app.get("/tufin-version", tags=["Test"], dependencies=[Depends(require_permission("test_tufin_connection"))])
async def test_tufin_connection(
    # Note: get_tufin_client dependency might be removed if client accessed via app.state
    tufin_client: TufinApiClient = Depends(get_tufin_client) 
):
    """
    Test endpoint to check connection to Tufin SecureTrack.
    Requires ADMIN permission.
    """
    logger.info("Testing Tufin connection via /tufin-version endpoint (Admin Permission Required).")
    try:
        # The actual client method now gets domains, not version
        # version_info = await tufin_client.get_securetrack_version()
        domains_info = await tufin_client.get_securetrack_domains() # Assuming this method exists now
        return {"message": "Successfully connected to Tufin SecureTrack", "domains_info": domains_info}
    except Exception as e:
        logger.error(f"Error during Tufin connection test: {e}", exc_info=True)
        # Re-raise the HTTPException that the client might have raised
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Internal error during Tufin connection test.")
    # No explicit close needed here if using lifespan management

# --- Server Startup ---
if __name__ == "__main__":
    # Use settings for port
    logger.info(f"Starting Tufin MCP Server on port {settings.MCP_PORT} with log level {settings.LOG_LEVEL}")
    # Note: For running with uvicorn directly from CLI, point to the app instance:
    # uvicorn src.app.main:app --reload --port <port>
    # The __main__ block might be less relevant if using a process manager or CLI runner
    uvicorn.run(app, host="0.0.0.0", port=settings.MCP_PORT)
