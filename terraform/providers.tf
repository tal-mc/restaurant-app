# =============================================================================
# PROVIDERS.TF - Terraform and Provider Configuration
# =============================================================================
# This file configures Terraform settings and the Azure provider.
# State is stored in Azure Storage for team collaboration and CI/CD access.
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }

  # =============================================================================
  # REMOTE BACKEND - Azure Storage
  # =============================================================================
  # State file stored in Azure Storage Account for:
  # - Team collaboration (shared state)
  # - CI/CD pipeline access
  # - State locking (prevents concurrent modifications)
  #
  # FIRST-TIME SETUP:
  # 1. Create storage account manually (one-time):
  #    az group create -n rg-terraform-state -l westeurope
  #    az storage account create -n tfstaterestaurant -g rg-terraform-state -l westeurope --sku Standard_LRS
  #    az storage container create -n tfstate --account-name tfstaterestaurant
  #
  # 2. Get storage account key:
  #    az storage account keys list -g rg-terraform-state -n tfstaterestaurant --query '[0].value' -o tsv
  #
  # 3. Set environment variable or use -backend-config:
  #    export ARM_ACCESS_KEY="<storage-account-key>"
  # =============================================================================
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "tfstaterestaurantdemo"
    container_name       = "tfstate"
    key                  = "restaurant-recommendation.tfstate"
  }
}

# =============================================================================
# AZURE PROVIDER
# =============================================================================
# Authentication via environment variables (set by GitHub Actions):
# - ARM_CLIENT_ID
# - ARM_CLIENT_SECRET
# - ARM_SUBSCRIPTION_ID
# - ARM_TENANT_ID
# =============================================================================
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}
