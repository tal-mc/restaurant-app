"""
Configuration management via environment variables.
Supports MongoDB Atlas (cloud) connection.
"""
import os


class Config:
    """Application configuration from environment variables."""
    
    # Database - MongoDB Atlas (cloud) connection string
    # Format: mongodb+srv://<user>:<password>@<cluster>.mongodb.net/<db>
    MONGODB_URI: str = os.getenv(
        "MONGODB_URI", 
        "mongodb://localhost:27017"  # Fallback for local testing only
    )
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "restaurant_db")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "restaurants")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # "json" or "text"
    
    # Data loading
    RESTAURANTS_FILE: str = os.getenv(
        "RESTAURANTS_FILE", 
        "/app/restaurants/restaurants.json"
    )


config = Config()
