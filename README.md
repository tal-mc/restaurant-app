# Restaurant Recommendation Service

A production-ready FastAPI microservice deployed on Azure using Terraform & GitHub Actions CI/CD.

---

## Architecture Overview

![High Level Diagram](high-level-diagram.png)

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| API | FastAPI + Python 3.11 | REST endpoint for queries |
| Database | MongoDB Atlas | Restaurant data storage |
| Container | Azure Container Instance | Runs Docker container |
| Logging | Log Analytics Workspace | Persistent log storage |
| State | Azure Storage | Terraform remote state |
| Registry | GitHub Container Registry | Docker image storage |
| CI/CD | GitHub Actions | Automated testing & deployment |
| Monitoring | UptimeRobot | External uptime monitoring |

---

## Running Locally

### Prerequisites

- Python 3.11+ OR Docker
- MongoDB Atlas account (free tier available)

### Option A: With Docker (Recommended)

```bash
# 1. Clone and configure
git clone https://github.com/USERNAME/restaurant-recommendation.git
cd restaurant-recommendation
cp .env.example .env
# Edit .env: set MONGODB_URI

# 2. Start API
docker-compose up -d api

# 3. Load data
docker-compose run --rm loader

# 4. Test
curl http://localhost:8080/health
curl "http://localhost:8080/rest?query=italian"

# 5. Stop
docker-compose down
```

### Option B: Without Docker

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment
export MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/restaurant_db"

# 4. Load data
python scripts/load_restaurants.py

# 5. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 6. Test
curl http://localhost:8080/health
```

---


## Project Structure


### Key directories

- **Application code** → [`app/`](./app/)
- **Data loader script** → [`scripts/`](./scripts/)
- **Restaurant data** → [`restaurants/`](./restaurants/)
- **Tests** → [`tests/`](./tests/)
- **Infrastructure as Code (Terraform)** → [`terraform/`](./terraform/)
- **CI/CD workflows** → [`.github/workflows/`](./.github/workflows/)

### Tree

```text
restaurant-recommendation/
├── app/                    # Application code
│   ├── config.py           # Configuration
│   ├── database.py         # MongoDB operations
│   ├── main.py             # FastAPI app (with logging)
│   ├── models.py           # Pydantic models
│   └── query_parser.py     # Query parsing
├── scripts/
│   └── load_restaurants.py # Data loader
├── restaurants/
│   └── restaurants.json    # Restaurant data
├── tests/                  # Unit tests
├── terraform/              # Infrastructure
├── .github/workflows/      # CI/CD
├── Dockerfile              # Multi-stage build
├── docker-compose.yml
├── requirements.txt
└── README.md

---

## Seeding Data

### Loading restaurants.json

```bash
# With Docker
docker-compose run --rm loader

# Without Docker
python scripts/load_restaurants.py
```

### Loader Behavior

| Exit Code | Meaning | Pipeline Behavior |
|-----------|---------|-------------------|
| 0 | All valid, inserted | ✅ Success |
| 1 | Some invalid (skipped), valid ones inserted | ✅ Success (logged) |
| 2 | Fatal error (bad JSON, DB unreachable) | ❌ Fails pipeline |

### Automated Loading in CI/CD

When `restaurants/restaurants.json` changes on `main`:
1. CI/CD automatically runs `load_restaurants.py`
2. Invalid rows are logged and skipped
3. Valid rows are inserted
4. Fatal errors (exit code 2) fail the pipeline

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Minimum coverage: 80%
pytest tests/ -v --cov=app --cov-fail-under=80
```

**Test Coverage:** 37 tests covering query parsing, validation, and models.

---

## Infrastructure with Terraform

### Directory Structure

```
[terraform/](./terraform/) 
├── providers.tf          # Azure provider + Storage backend
├── variables.tf          # Input variables
├── main.tf               # Resources (RG, Container, Log Analytics)
├── outputs.tf            # Output values
├── terraform.tfvars.example
└── .gitignore
```

### Resources Created

| Resource | Purpose |
|----------|---------|
| Resource Group | Container for all resources |
| Container Instance | Runs the API container |
| Log Analytics Workspace | Persistent logging (30 days) |

### First-Time Setup (State Backend)

```bash
# Create state storage (run once)
az group create -n rg-terraform-state -l westeurope
az storage account create -n tfstaterestaurant -g rg-terraform-state \
    -l westeurope --sku Standard_LRS
az storage container create -n tfstate --account-name tfstaterestaurant

# Get access key for TF_BACKEND_ACCESS_KEY secret
az storage account keys list -g rg-terraform-state \
    -n tfstaterestaurant --query '[0].value' -o tsv
```

### Manual Deployment

```bash
cd terraform
terraform init
terraform plan -var="docker_image=..." -var="mongodb_uri=..."
terraform apply -var="docker_image=..." -var="mongodb_uri=..."
```

### Importing Existing Resources

If resources already exist in Azure but not in Terraform state:

```bash
# Import existing resources
terraform import azurerm_resource_group.main \
  /subscriptions/<SUB_ID>/resourceGroups/rg-restaurant-api-dev

terraform import azurerm_container_group.api \
  /subscriptions/<SUB_ID>/resourceGroups/rg-restaurant-api-dev/providers/Microsoft.ContainerInstance/containerGroups/ci-restaurant-api-dev

terraform import azurerm_log_analytics_workspace.main \
  /subscriptions/<SUB_ID>/resourceGroups/rg-restaurant-api-dev/providers/Microsoft.OperationalInsights/workspaces/log-restaurant-api-dev
```

---

## CI/CD Pipeline

### Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Push PR    │────▶│   CI Tests   │────▶│  PR Ready    │
└──────────────┘     └──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Push Main   │────▶│ Build Image  │────▶│  Terraform   │────▶│ Load Data*   │
└──────────────┘     │ Push to GHCR │     │    Apply     │     │ Smoke Tests  │
                     └──────────────┘     └──────────────┘     └──────────────┘
                                                               * Only if restaurants.json changed
```

### Workflows

| Workflow | Trigger | Jobs |
|----------|---------|------|
| **ci.yml** | PR, Push | Test → Validate → Build Docker → Validate Terraform |
| **cd.yml** | Push to main | Build → Push GHCR → Terraform → Load Data → Smoke Test |

### Key Features

- **Terraform is idempotent:** Only changes what's different
- **Image tag:** Commit SHA for traceability
- **Data loading:** Automatic when `restaurants.json` changes
- **Smoke tests:** Verify deployment health

---

## Environment Variables & Secrets

### Local Development (.env)

```bash
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/restaurant_db
DATABASE_NAME=restaurant_db
PORT=8080
LOG_LEVEL=INFO
```

### GitHub Secrets (Required)

| Secret | Description |
|--------|-------------|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `AZURE_CREDENTIALS` | Azure service principal JSON |
| `TF_BACKEND_ACCESS_KEY` | Azure Storage access key |

### Creating Azure Service Principal

```bash
az ad sp create-for-rbac \
  --name "github-restaurant-app" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID> \
  --sdk-auth

# Copy entire JSON output to AZURE_CREDENTIALS secret
```

---

## Logging

### Request/Response Logging

Every `/rest` request is logged with:
- HTTP method, URL, query parameters
- The final result (list or message)
- Result type and count

Logging failures do not crash the app (wrapped in try/except).

### Log Analytics Integration

Application logs are shipped from Azure Container Instances to Log Analytics Workspace for:
- **Retention:** 30 days (configurable)
- **Querying:** Via Azure Portal or CLI
- **Troubleshooting:** Container stdout/stderr preserved

### Viewing Logs

```bash
# Azure Portal
Portal → Log Analytics → Logs → Query: ContainerInstanceLog_CL

# Azure CLI
az monitor log-analytics query \
  -w <workspace-id> \
  --analytics-query "ContainerInstanceLog_CL | order by TimeGenerated desc | take 50"
```

---


## API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rest?query=...` | Restaurant recommendations |
| GET | `/health` | Health check |
| GET | `/` | API info |

### Query Examples

```bash
curl "http://localhost:8080/rest?query=italian"
curl "http://localhost:8080/rest?query=vegetarian%20asian"
curl "http://localhost:8080/rest?query=steakhouse%20between%2010:00%20and%2022:00"
```

### Query Rules

| Feature | Pattern | Behavior |
|---------|---------|----------|
| Vegetarian | "vegetarian" in query | Returns vegetarian only |
| Non-vegetarian | No "vegetarian" | Returns **non-vegetarian only** |
| Style | italian/asian/steakhouse/mediterranean | First match wins |
| Time range | `between HH:MM and HH:MM` | Must be open entire range |

---

## Assumptions & Limitations

### Assumptions

| Assumption | Source |
|------------|--------|
| No "vegetarian" → non-vegetarian only | Company confirmed |
| Multiple styles → first match wins | Company confirmed |
| Server local time for "open now" | Company confirmed |
| Midnight crossing → validation error | Company confirmed |
| Skip invalid JSON entries | Default behavior |

### Simplifications

| Simplification | Future Improvement |
|----------------|-------------------|
| HTTP only (no TLS) | Add Application Gateway |
| Public IP exposure | VNet + NSG isolation |
| Single container | App Service / AKS for scaling |
| Secrets in env vars | Azure Key Vault |

### Known Limitations

| Limitation | Workaround |
|------------|------------|
| Midnight crossing (22:00-02:00) | Returns error message |
| Single timezone | Uses server local time |
| No pagination | Returns all results |
| No rate limiting | Add slowapi middleware |

---

## Future Improvements

### Infrastructure & Security

| Improvement | Description | Benefit |
|-------------|-------------|---------|
| **VNet + NSG** | Deploy in Virtual Network with Network Security Groups | Network isolation |
| **Private Endpoints** | MongoDB Atlas via Azure Private Link | No public internet |
| **Application Gateway** | TLS termination, WAF, Let's Encrypt | HTTPS, security |
| **Azure Key Vault** | Centralized secrets management | Better security |
| **App Service / AKS** | Migration from Container Instance | Production scaling, SLA |
| **Managed Identity** | Remove stored credentials | No secrets in pipeline |

### CI/CD Pipeline Improvements

| Improvement | Description | Benefit |
|-------------|-------------|---------|
| **Script-based stages** | Move logic to `scripts/ci/*.sh` returning 0/1, pipeline shows pass/fail only | Cleaner pipelines, easier debugging |
| **Separate infra pipeline** | Terraform in dedicated workflow or GitOps (e.g., Terraform Cloud) | Best practice separation of concerns |
| **Environment promotions** | dev → staging → prod with manual approvals | Safer deployments |

### Monitoring & Alerting

| Improvement | Description | Benefit |
|-------------|-------------|---------|
| **Azure Monitor** | Native Azure monitoring with alerts | Integrated ecosystem |
| **Application Insights** | APM for performance tracking | Detailed metrics, traces |
| **Alert notifications** | Slack/Teams/Email on pipeline success/failure | Team awareness |
| **PagerDuty/OpsGenie** | On-call alerting for production issues | Incident response |

### UI & Cosmetics

| Improvement | Description | Benefit |
|-------------|-------------|---------|
| **HTML frontend** | Simple web UI for the API | User-friendly demo |
| **Swagger customization** | Branded API documentation | Professional appearance |

---


