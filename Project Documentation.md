# Restaurant Recommendation Service - Technical Documentation

**Version:** 1.1.0  
**Status:** Production Ready

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 GITHUB                                      │
│  ┌────────────────┐         ┌──────────────────────────────────────────┐   │
│  │  Repository    │         │  GitHub Actions                          │   │
│  │  • app/        │────────▶│  CI: Test → Validate → Build             │   │
│  │  • terraform/  │         │  CD: Build → Push → Deploy → Load Data   │   │
│  │  • .github/    │         └──────────────┬───────────────────────────┘   │
│  └────────────────┘                        │                               │
│                                            │                               │
│  ┌────────────────┐                        │                               │
│  │  GHCR          │◄───────────────────────┤                               │
│  └───────┬────────┘                        │                               │
└──────────│─────────────────────────────────│───────────────────────────────┘
           │                                 │
           ▼                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  AZURE                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Resource Group: rg-restaurant-api-dev                                │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │  │  Container Instance: FastAPI on :8080                           │ │ │
│  │  └─────────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │  │  Log Analytics: Persistent logging (30 days)                    │ │ │
│  │  └─────────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
           │                            │
           ▼                            ▼
┌─────────────────────┐      ┌─────────────────────┐
│   MONGODB ATLAS     │      │    UPTIMEROBOT      │
│   restaurant_db     │      │   /health monitor   │
└─────────────────────┘      └─────────────────────┘
```

---

## 2. Project Structure

```
restaurant-recommendation/
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment configuration
│   ├── database.py            # MongoDB operations (class methods)
│   ├── main.py                # FastAPI app + request/response logging
│   ├── models.py              # Pydantic models
│   └── query_parser.py        # Query parsing (returns dict)
├── scripts/
│   └── load_restaurants.py    # Data loader (CI/CD automated)
├── restaurants/
│   └── restaurants.json
├── tests/
│   ├── test_api.py            # Model tests
│   ├── test_app_endpoints.py  # Endpoint tests
│   └── test_query_parser.py   # Parser tests
├── terraform/
│   ├── providers.tf
│   ├── variables.tf
│   ├── main.tf
│   └── outputs.tf
├── .github/workflows/
│   ├── ci.yml
│   └── cd.yml
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 3. File Documentation

app/config.py
app/models.py
app/query_parser.py
app/main.py


**Logging Implementation:**

```python
def safe_log(message: str, level: str = "info", **extra) -> None:
    """Never crashes the app - per spec requirement."""
    try:
        log_func = getattr(logger, level.lower(), logger.info)
        if extra:
            extra_str = json.dumps(extra, default=str)
            log_func(f"{message} | {extra_str}")
        else:
            log_func(message)
    except Exception:
        pass  # Fail silently
```

Every `/rest` request logs:
- HTTP method, URL, query parameters
- Result type (success/error/empty/no_results)
- Result count and full result

---

## 4. Logging Specification

### Requirements (from assignment)

> Every request to /rest should be logged with at least:
> - HTTP method, URL, query parameters
> - The final result (either the list or the message)
> - Logging failures do not crash the app

### Implementation

```python
# On request start
safe_log(
    "Incoming request",
    method=request.method,
    url=str(request.url),
    query_params=dict(request.query_params),
    endpoint="/rest"
)

# On request completion
safe_log(
    "Request completed",
    method=request.method,
    url=str(request.url),
    query_params=dict(request.query_params),
    result_type="success",
    result_count=len(restaurants),
    result=response_data
)
```

### Log Output Format

```json
{"timestamp": "2024-12-10 08:00:00", "level": "INFO", "module": "main", "message": "Request completed | {\"method\": \"GET\", \"url\": \"http://api:8080/rest?query=italian\", \"result_type\": \"success\", \"result_count\": 3}"}
```

---

## 5. Dockerfile (Multi-stage)

```dockerfile
# Stage 1: Builder - install dependencies
FROM python:3.11-slim AS builder
# Creates /opt/venv with all packages

# Stage 2: Runtime - minimal image
FROM python:3.11-slim AS runtime
# Copies only /opt/venv, no build tools
```

| Benefit | Description |
|---------|-------------|
| Smaller image | ~200 MB vs ~400 MB |
| Better security | No gcc, no build tools in production |
| Faster pulls | Less data to transfer |

---

## 6. API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/rest?query=...` | Restaurant recommendations |
| GET | `/health` | Health check (DB connectivity) |
| GET | `/` | API info and examples |

### Response Format

**Root endpoint** returns:
```json
{
  "service": "Restaurant Recommendation API",
  "version": "1.0.0",
  "endpoints": {...},
  "query_rules": {...},
  "examples": [...]
}
```

**Health endpoint** returns:
```json
{
  "status": "healthy",
  "database": "connected",
  "restaurant_count": 10
}
```

### Query Rules

| Input | Behavior |
|-------|----------|
| "vegetarian" present | `{vegetarian: "yes"}` |
| "vegetarian" absent | `{vegetarian: "no"}` |
| Style keyword | First match wins |
| No time | Use current server time |

---

## 7. Test Coverage

**45 Tests Total:**

| File | Tests | Coverage |
|------|-------|----------|
| test_api.py | 8 | Model validation |
| test_app_endpoints.py | 7 | API endpoint behavior |
| test_query_parser.py | 30 | Query parsing logic |

---

## 8. Environment Variables

### Application

| Variable | Required | Default |
|----------|----------|---------|
| `MONGODB_URI` | ✅ | - |
| `DATABASE_NAME` | - | `restaurant_db` |
| `COLLECTION_NAME` | - | `restaurants` |
| `PORT` | - | `8080` |
| `LOG_LEVEL` | - | `INFO` |
| `LOG_FORMAT` | - | `json` |

### GitHub Secrets

| Secret | Description |
|--------|-------------|
| `MONGODB_URI` | Atlas connection string |
| `AZURE_CREDENTIALS` | Service principal JSON |
| `TF_BACKEND_ACCESS_KEY` | Storage account key |

---

## 9. Terraform Resources

| Resource | Type | Purpose |
|----------|------|---------|
| Resource Group | `azurerm_resource_group` | Container for resources |
| Log Analytics | `azurerm_log_analytics_workspace` | Persistent logging |
| Container Instance | `azurerm_container_group` | Run application |

### Importing Existing Resources

If "resource already exists" error:

```bash
terraform import azurerm_resource_group.main \
  /subscriptions/<SUB>/resourceGroups/rg-restaurant-api-dev

terraform import azurerm_container_group.api \
  /subscriptions/<SUB>/resourceGroups/rg-restaurant-api-dev/providers/Microsoft.ContainerInstance/containerGroups/ci-restaurant-api-dev

terraform import azurerm_log_analytics_workspace.main \
  /subscriptions/<SUB>/resourceGroups/rg-restaurant-api-dev/providers/Microsoft.OperationalInsights/workspaces/log-restaurant-api-dev
```

---

## 10. Cost Estimate

| Resource | Monthly |
|----------|---------|
| Container Instance | ~$30 |
| Log Analytics | ~$5 |
| Storage (state) | ~$1 |
| MongoDB Atlas M0 | Free |
| **Total** | **~$36** |
