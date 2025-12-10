"""
Restaurant Recommendation Service - FastAPI Application

Endpoints:
- GET /rest?query=... - Get restaurant recommendations
- GET /health - Health check
- GET / - API info

LOGGING (per spec):
- Every /rest request logged with: method, URL, query params, result
- Logging failures do not crash the app
"""
import logging
import sys
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from app.config import config
from app.database import Database
from app.query_parser import process_query
from app.models import APIResponse


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Setup structured JSON logging to stdout."""
    try:
        log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        
        if config.LOG_FORMAT == "json":
            log_format = (
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"module": "%(module)s", "message": "%(message)s"}'
            )
        else:
            log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            stream=sys.stdout,
            force=True,
        )
    except Exception:
        pass  # Never crash on logging setup


setup_logging()
logger = logging.getLogger(__name__)


def safe_log(message: str, level: str = "info", **extra) -> None:
    """
    Log safely - never crash on logging failure.
    Per spec: "Make sure logging failures do not crash the app."
    """
    try:
        log_func = getattr(logger, level.lower(), logger.info)
        if extra:
            # Include extra data in message for JSON logs
            extra_str = json.dumps(extra, default=str)
            log_func(f"{message} | {extra_str}")
        else:
            log_func(message)
    except Exception:
        pass  # Fail silently per requirements


# =============================================================================
# APPLICATION LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    safe_log("Starting Restaurant Recommendation Service")
    try:
        await Database.connect()
        count = await Database.count()
        safe_log(f"Database ready with {count} restaurants")
    except Exception as e:
        safe_log(f"Database connection failed: {e}", level="error")
        raise
    
    yield
    
    safe_log("Shutting down")
    await Database.disconnect()


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Restaurant Recommendation Service",
    description="Find restaurants based on free-text queries",
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/rest", response_model=APIResponse)
async def get_recommendations(
    request: Request,
    query: Optional[str] = Query(None, description="Free-text search query")
) -> dict:
    """
    Get restaurant recommendations based on free-text query.
    
    LOGGING: Every request logs method, URL, query params, and result.
    """
    response_data = {"restaurantRecommendation": ""}
    
    try:
        # =====================================================================
        # LOG REQUEST (per spec requirement)
        # =====================================================================
        safe_log(
            "Incoming request",
            level="info",
            method=request.method,
            url=str(request.url),
            query_params=dict(request.query_params),
            endpoint="/rest"
        )
        
        # =====================================================================
        # HANDLE EMPTY QUERY
        # =====================================================================
        if not query or not query.strip():
            response_data["restaurantRecommendation"] = "query is empty"
            safe_log(
                "Request completed",
                level="info",
                method=request.method,
                url=str(request.url),
                result_type="empty_query",
                result=response_data
            )
            return response_data
        
        # =====================================================================
        # PARSE QUERY
        # =====================================================================
        result = process_query(query)
        
        # Handle parse errors (including midnight crossing)
        if result["error"]:
            response_data["restaurantRecommendation"] = result["error"]
            safe_log(
                "Request completed",
                level="info",
                method=request.method,
                url=str(request.url),
                result_type="parse_error",
                error=result["error"],
                result=response_data
            )
            return response_data
        
        # =====================================================================
        # QUERY DATABASE
        # =====================================================================
        restaurants = await Database.find_restaurants(result["filter"])
        
        # =====================================================================
        # BUILD AND LOG RESPONSE (per spec requirement)
        # =====================================================================
        if not restaurants:
            response_data["restaurantRecommendation"] = "There are no results."
            result_type = "no_results"
            result_count = 0
        else:
            response_data["restaurantRecommendation"] = restaurants
            result_type = "success"
            result_count = len(restaurants)
        
        safe_log(
            "Request completed",
            level="info",
            method=request.method,
            url=str(request.url),
            query_params=dict(request.query_params),
            result_type=result_type,
            result_count=result_count,
            mongo_filter=str(result["filter"]),
            result=response_data
        )
        
        return response_data
        
    except Exception as e:
        safe_log(f"Request error: {e}", level="error")
        return JSONResponse(
            status_code=500,
            content={"restaurantRecommendation": f"Internal error: {str(e)}"}
        )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for container orchestration."""
    try:
        count = await Database.count()
        return {
            "status": "healthy",
            "database": "connected",
            "restaurant_count": count
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


@app.get("/")
async def root() -> dict:
    """API information."""
    return {
        "service": "Restaurant Recommendation API",
        "version": "1.0.0",
        "endpoints": {
            "GET /rest?query=...": "Get restaurant recommendations",
            "GET /health": "Health check",
        },
        "query_rules": {
            "vegetarian": "If 'vegetarian' in query → vegetarian only, else → non-vegetarian only",
            "style": "First match wins: italian, asian, steakhouse, mediterranean",
            "time": "between X and Y, opens at X, closes at X, or current time (default)",
            "midnight_crossing": "NOT supported (e.g., 22:00-02:00 returns error)",
        },
        "examples": [
            "/rest?query=vegetarian italian restaurant",
            "/rest?query=asian restaurant between 10:00 and 18:30",
            "/rest?query=steakhouse closes at 23:00",
        ]
    }