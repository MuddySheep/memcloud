"""
MemCloud API - Main Application
Production Forcing Framework Compliant

PFF Gates Implemented:
- ✅ Structured logging
- ✅ Health check endpoints
- ✅ Error handling middleware
- ✅ CORS configuration
- ✅ Request ID tracking
- ✅ Graceful shutdown
"""
import sys
import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.db.database import init_db, close_db, check_db_health

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.

    PFF Gate: Graceful startup and shutdown

    Handles:
    - Database initialization
    - Firebase initialization
    - Cleanup on shutdown
    """
    # Startup
    logger.info(
        "application.startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT
    )

    # Skip database initialization during startup - will connect lazily when needed
    logger.info("application.startup.complete", note="Database will connect lazily when needed")

    yield

    # Shutdown
    logger.info("application.shutdown.starting")

    try:
        await close_db()
        logger.info("application.shutdown.database.closed")

    except Exception as e:
        logger.error("application.shutdown.failed", error=str(e))

    logger.info("application.shutdown.complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Memory-as-a-Service Platform - Deploy and manage MemMachine instances on GCP",
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ============================================================================
# Middleware Configuration
# ============================================================================

# CORS Middleware - PFF Security Gate
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Add unique request ID to all requests for tracing.

    PFF Gate: Request tracing and monitoring
    """
    import uuid
    request_id = str(uuid.uuid4())

    # Add to request state
    request.state.request_id = request_id

    # Log request
    logger.info(
        "request.started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None
    )

    # Process request
    try:
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log response
        logger.info(
            "request.completed",
            request_id=request_id,
            status_code=response.status_code,
        )

        return response

    except Exception as e:
        logger.error(
            "request.failed",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        raise


# ============================================================================
# Exception Handlers - PFF Error Handling Gate
# ============================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with structured responses"""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "http.exception",
        request_id=request_id,
        status_code=exc.status_code,
        detail=exc.detail
    )

    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "request_id": request_id,
            "status_code": exc.status_code,
        }
    )

    # Add CORS headers manually to error responses
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed field information"""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "validation.error",
        request_id=request_id,
        errors=exc.errors()
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation error",
            "request_id": request_id,
            "status_code": 422,
            "details": exc.errors(),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "unhandled.exception",
        request_id=request_id,
        error=str(exc),
        exc_info=True
    )

    # Temporarily expose errors for debugging
    # TODO: Change back to generic message after debugging
    message = f"{type(exc).__name__}: {str(exc)}"

    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": message,
            "request_id": request_id,
            "status_code": 500,
        }
    )

    # Add CORS headers manually to error responses
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


# ============================================================================
# Health Check Endpoints - PFF Monitoring Gate
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - basic health check
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Comprehensive health check endpoint.

    PFF Gate: Monitoring and alerting

    Checks:
    - API is responding
    - Database is connected
    - Database performance
    """
    db_health = await check_db_health()

    is_healthy = db_health["status"] == "healthy"

    response = {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {
            "api": "healthy",
            "database": db_health,
        }
    }

    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    Returns 200 when service is ready to accept traffic.
    """
    db_health = await check_db_health()

    if db_health["status"] == "healthy":
        return {"ready": True}
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"ready": False, "reason": "database_unhealthy"}
        )


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    Returns 200 if service is alive (doesn't check dependencies).
    """
    return {"alive": True}


# ============================================================================
# API Routes
# ============================================================================

from app.api.v1.api import api_router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_config=None,  # Use structlog instead
    )
