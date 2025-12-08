"""
Restaurant Recommendation Service - FastAPI Application

Endpoints:
- GET /rest?query=... - Get restaurant recommendations
- GET /health - Health check
- GET / - API info
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from app.config import config
from app.database import Database
from app.query_parser import process_query
from app.models import APIResponse


def setup_logging():
    """Setup logging based on config."""
    log_format = (
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
        if config.LOG_FORMAT == "json"
        else "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


setup_logging()
logger = logging.getLogger(__name__)


def safe_log(message: str, level: str = "info") -> None:
    """Log safely - never crash on logging failure."""
    try:
        getattr(logger, level, logger.info)(message)
    except Exception:
        pass  # Fail silently per requirements


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


app = FastAPI(
    title="Restaurant Recommendation Service",
    description="Find restaurants based on free-text queries",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/rest", response_model=APIResponse)
async def get_recommendations(
    request: Request,
    query: Optional[str] = Query(None, description="Free-text search query")
) -> dict:
    """
    Get restaurant recommendations based on free-text query.
    
    Query parsing rules:
    - vegetarian: If "vegetarian" in query → show vegetarian only, else → non-vegetarian only
    - style: First match wins (italian, asian, steakhouse, mediterranean)
    - time: between X and Y, opens at X, closes at X, or current server time
    - Midnight crossing (e.g., 22:00-02:00) is NOT supported
    
    Examples:
    - ?query=vegetarian italian restaurant
    - ?query=asian restaurant between 10:00 and 18:30
    - ?query=steakhouse closes at 23:00
    """
    response_data = {"restaurantRecommendation": ""}
    
    try:
        safe_log(f"Request: {request.method} {request.url.path} query={query}")
        
        # Handle empty/missing query
        if not query or not query.strip():
            response_data["restaurantRecommendation"] = "query is empty"
            safe_log(f"Response: {response_data}")
            return response_data
        
        # Parse query
        result = process_query(query)
        
        # Handle parse errors (including midnight crossing)
        if result["error"]:
            response_data["restaurantRecommendation"] = result["error"]
            safe_log(f"Response: {response_data}")
            return response_data
        
        # Query database
        restaurants = await Database.find_restaurants(result["filter"])
        
        # Format response
        if not restaurants:
            response_data["restaurantRecommendation"] = "There are no results."
        else:
            response_data["restaurantRecommendation"] = restaurants
        
        safe_log(f"Response: Found {len(restaurants) if restaurants else 0} restaurants")
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
