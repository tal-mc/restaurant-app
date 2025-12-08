"""
Pydantic models for restaurant data.
Strict validation: exactly required fields, no extra allowed.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Union
import re


# Required fields - must match exactly
REQUIRED_FIELDS = frozenset({"name", "style", "address", "vegetarian", "openHour", "closeHour"})


class Restaurant(BaseModel):
    """
    Restaurant data model.
    All fields required, no extra fields allowed.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, description="Restaurant name")
    style: str = Field(..., description="Cuisine style")
    address: str = Field(..., min_length=1, description="Restaurant address")
    vegetarian: str = Field(..., description="'yes' or 'no'")
    openHour: str = Field(..., description="Opening hour HH:MM")
    closeHour: str = Field(..., description="Closing hour HH:MM")

    @field_validator("vegetarian")
    @classmethod
    def validate_vegetarian(cls, v: str) -> str:
        """Normalize and validate vegetarian field."""
        v_lower = v.lower().strip()
        if v_lower not in ("yes", "no"):
            raise ValueError("must be 'yes' or 'no'")
        return v_lower

    @field_validator("style")
    @classmethod
    def validate_style(cls, v: str) -> str:
        """Normalize style to title case."""
        return v.strip().title()

    @field_validator("openHour", "closeHour")
    @classmethod
    def validate_time(cls, v: str) -> str:
        """Validate and normalize time to HH:MM format."""
        v = v.strip()
        
        # Try HH:MM format
        if match := re.match(r"^(\d{1,2}):(\d{2})$", v):
            hour, minute = int(match.group(1)), int(match.group(2))
        # Try HHMM format
        elif match := re.match(r"^(\d{2})(\d{2})$", v):
            hour, minute = int(match.group(1)), int(match.group(2))
        else:
            raise ValueError(f"Invalid time format: {v}. Use HH:MM or HHMM")
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Invalid time: {v}. Hour 0-23, minute 0-59")
        
        return f"{hour:02d}:{minute:02d}"


class RestaurantOut(BaseModel):
    """Restaurant output model (excludes MongoDB _id)."""
    name: str
    style: str
    address: str
    vegetarian: str
    openHour: str
    closeHour: str


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    restaurantRecommendation: Union[str, List[RestaurantOut]]
