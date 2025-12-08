"""
Tests for Pydantic models.
Run: pytest tests/test_api.py -v
"""
import pytest
from app.models import Restaurant, REQUIRED_FIELDS


class TestRestaurantModel:
    def test_valid_restaurant(self):
        r = Restaurant(
            name="Test Place",
            style="italian",
            address="123 Main St",
            vegetarian="yes",
            openHour="10:00",
            closeHour="22:00"
        )
        assert r.style == "Italian"
        assert r.vegetarian == "yes"
    
    def test_time_normalization(self):
        r = Restaurant(
            name="Test",
            style="Italian",
            address="123 Main St",
            vegetarian="no",
            openHour="0900",
            closeHour="2200"
        )
        assert r.openHour == "09:00"
        assert r.closeHour == "22:00"
    
    def test_invalid_vegetarian_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Restaurant(
                name="Test",
                style="Italian",
                address="123 Main St",
                vegetarian="maybe",
                openHour="10:00",
                closeHour="22:00"
            )
    
    def test_extra_field_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Restaurant(
                name="Test",
                style="Italian",
                address="123 Main St",
                vegetarian="yes",
                openHour="10:00",
                closeHour="22:00",
                rating=5
            )
    
    def test_missing_field_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Restaurant(
                name="Test",
                style="Italian",
                vegetarian="yes",
                openHour="10:00",
                closeHour="22:00"
            )


class TestRequiredFields:
    def test_required_fields_set(self):
        expected = {"name", "style", "address", "vegetarian", "openHour", "closeHour"}
        assert REQUIRED_FIELDS == expected
    
    def test_extra_fields_detected(self):
        data = {
            "name": "Test", "style": "Italian", "address": "123 St",
            "vegetarian": "yes", "openHour": "10:00", "closeHour": "22:00",
            "extra": "field"
        }
        extra = set(data.keys()) - REQUIRED_FIELDS
        assert extra == {"extra"}
    
    def test_missing_fields_detected(self):
        data = {"name": "Test", "style": "Italian"}
        missing = REQUIRED_FIELDS - set(data.keys())
        assert missing == {"address", "vegetarian", "openHour", "closeHour"}
