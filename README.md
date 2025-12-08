# Restaurant Recommendation Service

A RESTful API that returns restaurant recommendations based on free-text natural language queries.

## Quick Start

### Prerequisites

1. **MongoDB Atlas Account** (required - cloud database)
   - Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Create free account → Create M0 (free) cluster
   - Create database user with password
   - Whitelist your IP (Network Access → Add IP Address)
   - Get connection string: Click "Connect" → "Connect your application"

2. **Python 3.11+** or **Docker**

### Option 1: Docker (Recommended)

```bash
# 1. Clone and enter directory
cd restaurant-recommendation

# 2. Create .env file with your MongoDB Atlas connection
cp .env.example .env
# Edit .env and set MONGODB_URI to your Atlas connection string

# 3. Build and start
docker-compose up -d api

# 4. Load restaurant data
docker-compose run --rm loader

# 5. Test the API
curl "http://localhost:8080/rest?query=vegetarian%20italian"
```

### Option 2: Local Python

```bash
# 1. Setup environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Set MongoDB Atlas connection
export MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/restaurant_db"

# 3. Load data
python scripts/load_restaurants.py

# 4. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8080

# 5. Test
curl "http://localhost:8080/rest?query=vegetarian%20italian"
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rest?query=...` | Get restaurant recommendations |
| GET | `/health` | Health check |
| GET | `/` | API information |

### Example Queries

```bash
# Vegetarian Italian restaurant (open now)
curl "http://localhost:8080/rest?query=vegetarian%20italian%20restaurant"

# Asian restaurant between specific hours
curl "http://localhost:8080/rest?query=asian%20between%2010:00%20and%2018:30"

# Steakhouse that closes at 23:00
curl "http://localhost:8080/rest?query=steakhouse%20closes%20at%2023:00"

# Mediterranean vegetarian opening at 11:30
curl "http://localhost:8080/rest?query=mediterranean%20vegetarian%20opening%20at%2011:30"
```

### Response Formats

```json
// Success with results
{ "restaurantRecommendation": [{ "name": "...", "style": "...", ... }] }

// No results
{ "restaurantRecommendation": "There are no results." }

// Empty query
{ "restaurantRecommendation": "query is empty" }

// Invalid time
{ "restaurantRecommendation": "Invalid time format: 25:99" }

// Midnight crossing (not supported)
{ "restaurantRecommendation": "Time ranges crossing midnight are not supported: 22:00 to 02:00" }
```

## Query Parsing Rules

| Feature | Behavior | Example |
|---------|----------|---------|
| **Vegetarian** | `vegetarian` in query → show vegetarian only | `vegetarian restaurant` |
| **Non-vegetarian** | No `vegetarian` → show **only non-vegetarian** | `italian restaurant` |
| **Style** | **First match wins**: italian, asian, steakhouse, mediterranean | `italian and mediterranean` → Italian only |
| **Time Range** | `between HH:MM and HH:MM` | `between 10:00 and 18:30` |
| **Opens At** | `opens at HH:MM` or `opening at HH:MM` | `opens at 11:30` |
| **Closes At** | `closes at HH:MM` or `closing at HH:MM` | `closes at 23:00` |
| **Open Now** | No time specified → **server local time** | `italian restaurant` |
| **Midnight** | Ranges crossing midnight → **validation error** | `between 22:00 and 02:00` → error |

## Data Model

### Restaurant Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Restaurant name |
| `style` | string | ✅ | Cuisine: Italian, Asian, Steakhouse, Mediterranean |
| `address` | string | ✅ | Physical address |
| `vegetarian` | string | ✅ | "yes" or "no" |
| `openHour` | string | ✅ | Opening time (HH:MM) |
| `closeHour` | string | ✅ | Closing time (HH:MM) |

### Validation Rules

- Exactly 6 fields (no extra fields allowed)
- `vegetarian` must be "yes" or "no"
- Time format: HH:MM or HHMM
- Unique constraint: name + address

### Adding Restaurants

1. Edit `restaurants/restaurants.json`
2. Run loader:
   ```bash
   # Docker
   docker-compose run --rm loader
   
   # Local
   python scripts/load_restaurants.py
   ```

**Invalid entries are skipped** (logged, but don't block valid entries).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | (required) | MongoDB Atlas connection string |
| `DATABASE_NAME` | `restaurant_db` | Database name |
| `PORT` | `8080` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | Log format (json/text) |

## Project Structure

```
restaurant-recommendation/
├── app/
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models
│   ├── database.py       # MongoDB Atlas connection
│   ├── query_parser.py   # Free-text parsing
│   └── config.py         # Environment config
├── scripts/
│   └── load_restaurants.py
├── restaurants/
│   └── restaurants.json
├── tests/
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Testing

```bash
# Run unit tests
pytest tests/ -v
```

## Known Limitations

| Limitation | Description |
|------------|-------------|
| Midnight crossing | Hours like 22:00-02:00 not supported (returns error) |
| Timezone | Uses server local time |
| Pagination | Returns all results (no limit) |
| Multiple styles | First match wins |

## Design Decisions

These behaviors were **confirmed by the company**:

1. ✅ No "vegetarian" in query → return **only non-vegetarian**
2. ✅ Multiple styles → **first match wins**
3. ✅ No time specified → use **server local time**
4. ✅ Midnight crossing → return **validation error**
5. ✅ No pagination needed
6. ✅ Use **cloud MongoDB** (Atlas)
7. ✅ **Skip invalid entries** in data loader (log errors, continue)
