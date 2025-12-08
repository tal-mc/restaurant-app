"""
Unit tests for query parser.
Run: pytest tests/test_query_parser.py -v
"""
import pytest
from app.query_parser import (
    normalize_time,
    parse_vegetarian,
    parse_style,
    parse_time_constraints,
    parse_query,
    process_query,
    QueryParseError,
)


class TestNormalizeTime:
    def test_hhmm_with_colon(self):
        assert normalize_time("10:30") == "10:30"
        assert normalize_time("09:00") == "09:00"
        assert normalize_time("23:59") == "23:59"
    
    def test_hhmm_without_colon(self):
        assert normalize_time("1030") == "10:30"
        assert normalize_time("0900") == "09:00"
    
    def test_single_digit_hour(self):
        assert normalize_time("9:30") == "09:30"
    
    def test_invalid_hour_raises(self):
        with pytest.raises(QueryParseError, match="Invalid time"):
            normalize_time("25:00")
    
    def test_invalid_minute_raises(self):
        with pytest.raises(QueryParseError, match="Invalid time"):
            normalize_time("10:99")
    
    def test_invalid_format_raises(self):
        with pytest.raises(QueryParseError, match="Invalid time"):
            normalize_time("abc")


class TestParseVegetarian:
    def test_vegetarian_present_returns_yes(self):
        assert parse_vegetarian("a vegetarian restaurant") == "yes"
        assert parse_vegetarian("VEGETARIAN place") == "yes"
    
    def test_vegetarian_absent_returns_no(self):
        """Per company: if no 'vegetarian', return only non-vegetarian."""
        assert parse_vegetarian("italian restaurant") == "no"
        assert parse_vegetarian("steakhouse") == "no"


class TestParseStyle:
    def test_italian(self):
        assert parse_style("italian restaurant") == "Italian"
        assert parse_style("ITALIAN food") == "Italian"
    
    def test_asian(self):
        assert parse_style("asian cuisine") == "Asian"
    
    def test_steakhouse(self):
        assert parse_style("good steakhouse") == "Steakhouse"
    
    def test_mediterranean(self):
        assert parse_style("mediterranean") == "Mediterranean"
    
    def test_no_style_returns_none(self):
        assert parse_style("vegetarian restaurant") is None
    
    def test_first_match_wins(self):
        """Per company: first match wins."""
        result = parse_style("italian and mediterranean")
        assert result == "Italian"


class TestParseTimeConstraints:
    def test_between_with_and(self):
        open_by, close_by, use_current = parse_time_constraints("between 10:00 and 18:30")
        assert open_by == "10:00"
        assert close_by == "18:30"
        assert use_current is False
    
    def test_between_with_to(self):
        open_by, close_by, _ = parse_time_constraints("between 10:00 to 18:30")
        assert open_by == "10:00"
        assert close_by == "18:30"
    
    def test_closes_at(self):
        open_by, close_by, use_current = parse_time_constraints("closes at 23:00")
        assert open_by is None
        assert close_by == "23:00"
        assert use_current is False
    
    def test_opening_at(self):
        open_by, close_by, _ = parse_time_constraints("opening at 11:30")
        assert open_by == "11:30"
        assert close_by is None
    
    def test_no_time_uses_current(self):
        """Per company: use server local time."""
        _, _, use_current = parse_time_constraints("italian restaurant")
        assert use_current is True
    
    def test_midnight_crossing_raises_error(self):
        """Per company: midnight crossing NOT supported."""
        with pytest.raises(QueryParseError, match="midnight"):
            parse_time_constraints("between 22:00 and 02:00")
    
    def test_midnight_crossing_reverse_order(self):
        """23:00 to 01:00 should also fail."""
        with pytest.raises(QueryParseError, match="midnight"):
            parse_time_constraints("between 23:00 and 01:00")


class TestParseQuery:
    def test_empty_query_raises(self):
        with pytest.raises(QueryParseError, match="empty"):
            parse_query("")
    
    def test_whitespace_only_raises(self):
        with pytest.raises(QueryParseError, match="empty"):
            parse_query("   ")
    
    def test_full_query_parsing(self):
        parsed = parse_query("vegetarian italian restaurant")
        assert parsed.vegetarian == "yes"
        assert parsed.style == "Italian"
        assert parsed.use_current_time is True
    
    def test_non_vegetarian_default(self):
        parsed = parse_query("asian restaurant")
        assert parsed.vegetarian == "no"


class TestProcessQuery:
    def test_valid_query_returns_filter(self):
        result = process_query("vegetarian italian")
        assert result["error"] is None
        assert result["filter"]["vegetarian"] == "yes"
        assert result["filter"]["style"] == "Italian"
    
    def test_empty_query_returns_error(self):
        result = process_query("")
        assert result["error"] == "query is empty"
        assert result["filter"] is None
    
    def test_invalid_time_returns_error(self):
        result = process_query("restaurant closes at 25:99")
        assert "Invalid time" in result["error"]
    
    def test_midnight_crossing_returns_error(self):
        """Per company: return clear validation error."""
        result = process_query("restaurant between 22:00 and 02:00")
        assert "midnight" in result["error"].lower()
        assert result["filter"] is None
