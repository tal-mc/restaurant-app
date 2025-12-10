#!/usr/bin/env python3
"""
Restaurant Data Loader

Validates restaurants.json and loads into MongoDB Atlas (cloud).
- Skips invalid entries (logs errors, continues processing)
- Skips duplicates (same name + address)
- Reports summary at end

Exit codes:
- 0: All valid entries loaded successfully
- 1: Some entries were invalid (but valid ones loaded)
- 2: Fatal error (file not found, DB connection failed)
"""
import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError
from app.models import Restaurant, REQUIRED_FIELDS
from app.database import Database
from app.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def validate_restaurant(data: Dict[str, Any], index: int) -> Tuple[bool, Restaurant | None, Dict]:
    """
    Validate a single restaurant entry.
    Returns: (is_valid, Restaurant or None, error_details)
    """
    errors = {
        "index": index,
        "data": data,
        "missing_fields": [],
        "extra_fields": [],
        "validation_errors": []
    }
    
    if isinstance(data, dict):
        data_fields = set(data.keys())
        errors["missing_fields"] = list(REQUIRED_FIELDS - data_fields)
        errors["extra_fields"] = list(data_fields - REQUIRED_FIELDS)
    else:
        errors["validation_errors"].append(f"Expected object, got {type(data).__name__}")
        return False, None, errors
    
    if errors["missing_fields"] or errors["extra_fields"]:
        return False, None, errors
    
    try:
        restaurant = Restaurant(**data)
        return True, restaurant, {}
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            errors["validation_errors"].append(f"{field}: {err['msg']}")
        return False, None, errors


def load_json_file(filepath: str) -> Tuple[List[Dict], str | None]:
    """Load JSON file. Returns (data, error_message)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            return [], f"Expected JSON array, got {type(data).__name__}"
        
        return data, None
    except FileNotFoundError:
        return [], f"File not found: {filepath}"
    except json.JSONDecodeError as e:
        return [], f"Invalid JSON: {e}"


def log_validation_error(errors: Dict) -> None:
    """Log validation error with full details."""
    logger.error("=" * 50)
    logger.error(f"INVALID ENTRY at index {errors['index']}")
    logger.error(f"Data: {json.dumps(errors['data'], indent=2, default=str)}")
    
    if errors["missing_fields"]:
        logger.error(f"Missing fields: {errors['missing_fields']}")
    if errors["extra_fields"]:
        logger.error(f"Extra fields: {errors['extra_fields']}")
    if errors["validation_errors"]:
        for err in errors["validation_errors"]:
            logger.error(f"Validation: {err}")
    
    logger.error("=" * 50)


async def load_restaurants(filepath: str) -> Dict[str, int]:
    """Main loader function."""
    stats = {"inserted": 0, "skipped": 0, "invalid": 0, "total": 0}
    
    logger.info(f"Loading from: {filepath}")
    raw_data, error = load_json_file(filepath)
    
    if error:
        logger.error(error)
        raise RuntimeError(error)
    
    stats["total"] = len(raw_data)
    logger.info(f"Found {stats['total']} entries in file")
    
    # Connect to MongoDB Atlas
    logger.info("Connecting to MongoDB Atlas...")
    await Database.connect()
    
    for index, entry in enumerate(raw_data):
        is_valid, restaurant, errors = validate_restaurant(entry, index)
        
        if not is_valid:
            stats["invalid"] += 1
            log_validation_error(errors)
            continue
        
        inserted = await Database.insert_restaurant(restaurant.model_dump())
        
        if inserted:
            stats["inserted"] += 1
            logger.info(f"✓ Inserted: {restaurant.name}")
        else:
            stats["skipped"] += 1
            logger.info(f"→ Skipped (exists): {restaurant.name} at {restaurant.address}")
    
    await Database.disconnect()
    return stats


def main():
    """Entry point."""
    # Check for MONGODB_URI
    if "MONGODB_URI" not in os.environ:
        logger.warning("MONGODB_URI not set. Using default (localhost).")
        logger.warning("For production, set MONGODB_URI to your MongoDB Atlas connection string.")
    
    filepath = os.getenv("RESTAURANTS_FILE")
    if not filepath:
        filepath = Path(__file__).parent.parent / "restaurants" / "restaurants.json"
    
    try:
        stats = asyncio.run(load_restaurants(str(filepath)))
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(2)
    
    print("\n" + "=" * 40)
    print("LOAD SUMMARY")
    print("=" * 40)
    print(f"  Total entries:  {stats['total']}")
    print(f"  Inserted:       {stats['inserted']}")
    print(f"  Skipped:        {stats['skipped']} (already exist)")
    print(f"  Invalid:        {stats['invalid']} (validation errors)")
    print("=" * 40)
    
    if stats["invalid"] > 0:
        print("\n⚠ Some entries were invalid. Check logs above.")
        sys.exit(1)
    else:
        print("\n✓ All entries processed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
