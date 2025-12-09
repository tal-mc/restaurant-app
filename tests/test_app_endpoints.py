# tests/test_app_endpoints.py
"""
Integration-ish tests for the FastAPI app.

Goals:
- Hit real HTTP endpoints (/, /health, /rest).
- Exercise app.main logic and configuration.
- Avoid real MongoDB by monkeypatching Database methods.
"""

import pytest
from httpx import AsyncClient

from app.main import app
from app.database import Database


@pytest.mark.asyncio
async def test_root_endpoint():
    """
    Basic smoke test for GET /.
    Should return service metadata and endpoint info.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200

        data = resp.json()
        assert data["service"] == "Restaurant Recommendation API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "GET /rest?query=..." in data["endpoints"]
        assert "GET /health" in data["endpoints"]


@pytest.mark.asyncio
async def test_health_healthy(monkeypatch):
    """
    GET /health when database is "healthy".
    We stub Database.count() so no real MongoDB is needed.
    """

    async def fake_count():
        return 5

    monkeypatch.setattr(Database, "count", fake_count)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["restaurant_count"] == 5


@pytest.mark.asyncio
async def test_health_unhealthy(monkeypatch):
    """
    GET /health when database is "unhealthy".
    We simulate a failure by having Database.count() raise.
    """

    async def fake_count():
        raise Exception("DB down for maintenance")

    monkeypatch.setattr(Database, "count", fake_count)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 503

        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "DB down" in data["error"]


@pytest.mark.asyncio
async def test_rest_empty_query():
    """
    GET /rest without a query should return 'query is empty'
    and MUST NOT talk to the database.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/rest")
        assert resp.status_code == 200

        data = resp.json()
        assert data["restaurantRecommendation"] == "query is empty"


@pytest.mark.asyncio
async def test_rest_valid_query_with_results(monkeypatch):
    """
    Happy-path GET /rest with a valid query.
    We stub Database.find_restaurants() to return fake data.
    """

    fake_restaurants = [
        {
            "name": "Pasta Delight",
            "style": "Italian",
            "address": "Maskit St 35, Herzliya",
            "vegetarian": "yes",
            "openHour": "10:00",
            "closeHour": "22:00",
        }
    ]

    async def fake_find_restaurants(query):
        # We don't care about the actual filter here – that's covered in unit tests.
        return fake_restaurants

    monkeypatch.setattr(Database, "find_restaurants", fake_find_restaurants)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/rest", params={"query": "vegetarian italian restaurant"})
        assert resp.status_code == 200

        data = resp.json()
        recs = data["restaurantRecommendation"]
        assert isinstance(recs, list)
        assert len(recs) == 1
        assert recs[0]["name"] == "Pasta Delight"


@pytest.mark.asyncio
async def test_rest_valid_query_no_results(monkeypatch):
    """
    GET /rest with valid query but no restaurants found.
    Should return the 'There are no results.' message.
    """

    async def fake_find_restaurants(query):
        return []

    monkeypatch.setattr(Database, "find_restaurants", fake_find_restaurants)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/rest", params={"query": "asian restaurant"})
        assert resp.status_code == 200

        data = resp.json()
        assert data["restaurantRecommendation"] == "There are no results."


@pytest.mark.asyncio
async def test_rest_midnight_crossing_error():
    """
    GET /rest with a query that triggers the 'midnight crossing' validation error.
    In this case, main.py should return the error message directly
    without calling the database.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get(
            "/rest",
            params={"query": "restaurant between 22:00 and 02:00"},
        )
        assert resp.status_code == 200

        data = resp.json()
        # process_query() returns an error string that includes the word 'midnight'
        assert "midnight" in data["restaurantRecommendation"].lower()


@pytest.mark.asyncio
async def test_rest_internal_error_from_database(monkeypatch):
    """
    GET /rest when Database.find_restaurants() blows up.
    main.py should catch the exception and return a 500 with an error message.
    """

    async def fake_find_restaurants(query):
        raise Exception("Something bad happened in DB")

    monkeypatch.setattr(Database, "find_restaurants", fake_find_restaurants)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/rest", params={"query": "vegetarian italian"})
        assert resp.status_code == 500

        data = resp.json()
        assert "restaurantRecommendation" in data
        assert "Internal error" in data["restaurantRecommendation"]
