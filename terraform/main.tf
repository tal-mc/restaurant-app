# =============================================================================
# MAIN.TF - Azure Resources
# =============================================================================
# Creates the following resources:
# - Resource Group (container for all resources)
# - Container Instance (runs the Docker container)
#
# Future improvements (see README):
# - VNet + NSG for network isolation
# - Key Vault for secrets management
# - Application Gateway for HTTPS/TLS
# - App Service or AKS for production scaling
# =============================================================================

# -----------------------------------------------------------------------------
# RESOURCE GROUP
# -----------------------------------------------------------------------------
# Logical container for all related Azure resources.
# Deleting the resource group deletes all contained resources.
# -----------------------------------------------------------------------------

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = local.common_tags
}

# -----------------------------------------------------------------------------
# LOG ANALYTICS WORKSPACE (Persistent Logging)
# -----------------------------------------------------------------------------
# Container logs are shipped here for retention and querying.
# Query logs via Azure Portal → Log Analytics → Logs (Kusto)
# -----------------------------------------------------------------------------

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# CONTAINER INSTANCE
# -----------------------------------------------------------------------------
# Runs the Docker container with the FastAPI application.
# Uses public IP for simplicity (see Future Improvements for VNet option).
# -----------------------------------------------------------------------------

resource "azurerm_container_group" "api" {
  name                = "ci-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Public"
  dns_name_label      = local.resource_prefix
  restart_policy      = "Always"

  # ---------------------------------------------------------------------------
  # CONTAINER CONFIGURATION
  # ---------------------------------------------------------------------------
  container {
    name   = "api"
    image  = var.docker_image
    cpu    = var.cpu_cores
    memory = var.memory_gb

    ports {
      port     = 8080
      protocol = "TCP"
    }

    # Non-sensitive environment variables
    environment_variables = {
      "PORT"       = "8080"
      "LOG_LEVEL"  = var.log_level
      "LOG_FORMAT" = "json"
    }

    # Sensitive environment variables (not shown in Azure Portal)
    secure_environment_variables = {
      "MONGODB_URI" = var.mongodb_uri
    }

    # -------------------------------------------------------------------------
    # HEALTH PROBES
    # -------------------------------------------------------------------------
    # Liveness: Restarts container if unhealthy
    # Readiness: Stops traffic if not ready
    #note : adjust hardcoded vars to generalize.
    # -------------------------------------------------------------------------

    liveness_probe {
      http_get {
        path   = "/health"
        port   = 8080
        scheme = "Http"
      }
      initial_delay_seconds = 30
      period_seconds        = 30
      failure_threshold     = 3
      success_threshold     = 1
      timeout_seconds       = 5
    }

    readiness_probe {
      http_get {
        path   = "/health"
        port   = 8080
        scheme = "Http"
      }
      initial_delay_seconds = 10
      period_seconds        = 10
      failure_threshold     = 3
      success_threshold     = 1
      timeout_seconds       = 5
    }
  }

  # ---------------------------------------------------------------------------
  # LOG ANALYTICS INTEGRATION
  # ---------------------------------------------------------------------------
  # Ships container stdout/stderr to Log Analytics Workspace
  # ---------------------------------------------------------------------------
  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.main.workspace_id
      workspace_key = azurerm_log_analytics_workspace.main.primary_shared_key
      log_type      = "ContainerInsights"
    }
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

