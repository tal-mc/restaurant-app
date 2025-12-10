"""
Free-text query parser for restaurant recommendations.

Parsing rules (confirmed by company):
- vegetarian: if word appears → filter "yes", else → filter "no"
- style: first match wins (italian, asian, steakhouse, mediterranean)
- time: between X and Y, opens at X, closes at X, or current server time
- midnight crossing: NOT supported, return validation error
"""
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Supported cuisine styles (first match wins)
STYLES = {
    "italian": "Italian",
    "asian": "Asian", 
    "steakhouse": "Steakhouse",
    "mediterranean": "Mediterranean",
}


class QueryParseError(Exception):
    """Raised when query cannot be parsed."""
    pass


@dataclass
class ParsedQuery:
    """Result of parsing a free-text query."""
    vegetarian: str
    style: Optional[str]
    open_by: Optional[str]  # openHour must be <= this
    close_by: Optional[str]  # closeHour must be >= this
    use_current_time: bool
    raw_query: str


def normalize_time(time_str: str) -> str:
    """
    Normalize time to HH:MM format.
    Accepts: HH:MM, H:MM, HHMM
    Raises QueryParseError for invalid times.
    """
    time_str = time_str.strip()
    
    # Try HH:MM or H:MM
    if match := re.match(r"^(\d{1,2}):(\d{2})$", time_str):
        hour, minute = int(match.group(1)), int(match.group(2))
    # Try HHMM
    elif match := re.match(r"^(\d{2})(\d{2})$", time_str):
        hour, minute = int(match.group(1)), int(match.group(2))
    else:
        raise QueryParseError(f"Invalid time format: {time_str}")
    
    if not (0 <= hour <= 23):
        raise QueryParseError(f"Invalid time format: {time_str}")
    if not (0 <= minute <= 59):
        raise QueryParseError(f"Invalid time format: {time_str}")
    
    return f"{hour:02d}:{minute:02d}"


def get_current_time() -> str:
    """Get current server LOCAL time as HH:MM."""
    return datetime.now().strftime("%H:%M")


def parse_vegetarian(query: str) -> str:
    """
    Extract vegetarian preference.
    - If 'vegetarian' appears → return 'yes'
    - Otherwise → return 'no' (show only non-vegetarian)
    """
    return "yes" if "vegetarian" in query.lower() else "no"


def parse_style(query: str) -> Optional[str]:
    """
    Extract cuisine style.
    FIRST MATCH WINS (as confirmed by company).
    Returns normalized style name or None.
    """
    query_lower = query.lower()
    for key, value in STYLES.items():
        if key in query_lower:
            return value
    return None


def parse_time_constraints(query: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Extract time constraints from query.
    
    Returns: (open_by, close_by, use_current_time)
    
    Raises QueryParseError for midnight crossing (e.g., 22:00-02:00)
    """
    query_lower = query.lower()
    
    # Pattern: between HH:MM and HH:MM (or "to" or "-")
    between_patterns = [
        r"between\s+(\d{1,2}:\d{2})\s+(?:and|to)\s+(\d{1,2}:\d{2})",
        r"between\s+(\d{4})\s+(?:and|to|-)\s+(\d{4})",
        r"between\s+(\d{4})-(\d{4})",
        r"between\s+(\d{1,2}:\d{2})-(\d{1,2}:\d{2})",
    ]
    
    for pattern in between_patterns:
        if match := re.search(pattern, query_lower):
            start = normalize_time(match.group(1))
            end = normalize_time(match.group(2))
            
            # Check for midnight crossing (NOT SUPPORTED)
            if start > end:
                raise QueryParseError(
                    f"Time ranges crossing midnight are not supported: {start} to {end}"
                )
            
            return (start, end, False)
    
    # Pattern: opens/opening at HH:MM
    opens_patterns = [
        r"(?:opens?|opening)\s+(?:at\s+)?(\d{1,2}:\d{2})",
        r"(?:opens?|opening)\s+(?:at\s+)?(\d{4})",
    ]
    
    for pattern in opens_patterns:
        if match := re.search(pattern, query_lower):
            time = normalize_time(match.group(1))
            return (time, None, False)
    
    # Pattern: closes/closing at HH:MM
    closes_patterns = [
        r"(?:closes?|closing)\s+(?:at\s+)?(\d{1,2}:\d{2})",
        r"(?:closes?|closing)\s+(?:at\s+)?(\d{4})",
    ]
    
    for pattern in closes_patterns:
        if match := re.search(pattern, query_lower):
            time = normalize_time(match.group(1))
            return (None, time, False)
    
    # No explicit time → use current server LOCAL time
    return (None, None, True)


def parse_query(query: str) -> ParsedQuery:
    """
    Parse free-text query into structured filters.
    Raises QueryParseError for invalid input.
    """
    if not query or not query.strip():
        raise QueryParseError("query is empty")
    
    query = query.strip()
    
    vegetarian = parse_vegetarian(query)
    style = parse_style(query)
    open_by, close_by, use_current = parse_time_constraints(query)
    
    return ParsedQuery(
        vegetarian=vegetarian,
        style=style,
        open_by=open_by,
        close_by=close_by,
        use_current_time=use_current,
        raw_query=query
    )


def build_mongo_filter(parsed: ParsedQuery) -> Dict[str, Any]:
    """Convert ParsedQuery to MongoDB query filter."""
    mongo_filter: Dict[str, Any] = {}
    
    # Always filter by vegetarian
    mongo_filter["vegetarian"] = parsed.vegetarian
    
    # Optional style filter (first match was already selected)
    if parsed.style:
        mongo_filter["style"] = parsed.style
    
    # Time filters
    if parsed.use_current_time:
        now = get_current_time()
        mongo_filter["openHour"] = {"$lte": now}
        mongo_filter["closeHour"] = {"$gte": now}
    else:
        if parsed.open_by:
            mongo_filter["openHour"] = {"$lte": parsed.open_by}
        if parsed.close_by:
            mongo_filter["closeHour"] = {"$gte": parsed.close_by}
    
    return mongo_filter


def process_query(query: str) -> Dict[str, Any]:
    """
    Main entry point: parse query and build MongoDB filter.
    
    Returns dict with:
    - filter: MongoDB query dict (or None on error)
    - parsed: ParsedQuery object (or None on error)
    - error: Error message (or None on success)
    """
    try:
        parsed = parse_query(query)
        mongo_filter = build_mongo_filter(parsed)
        
        logger.info(f"Query parsed: vegetarian={parsed.vegetarian}, "
                   f"style={parsed.style}, time_filter={parsed.use_current_time}")
        
        return {
            "filter": mongo_filter,
            "parsed": parsed,
            "error": None
        }
    except QueryParseError as e:
        logger.warning(f"Query parse error: {e}")
        return {
            "filter": None,
            "parsed": None,
            "error": str(e)
        }
