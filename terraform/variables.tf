# =============================================================================
# VARIABLES.TF - Input Variables
# =============================================================================
# All configurable parameters for the infrastructure.
# Sensitive values should be passed via environment variables or CI/CD secrets.
# =============================================================================

# -----------------------------------------------------------------------------
# REQUIRED VARIABLES (no defaults - must be provided)
# -----------------------------------------------------------------------------

variable "docker_image" {
  description = "Full Docker image URL including tag (e.g., ghcr.io/user/repo:sha)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9./-]+:[a-zA-Z0-9._-]+$", var.docker_image))
    error_message = "Docker image must be in format 'registry/image:tag'."
  }
}

variable "mongodb_uri" {
  description = "MongoDB Atlas connection string (mongodb+srv://...)"
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^mongodb(\\+srv)?://", var.mongodb_uri))
    error_message = "MongoDB URI must start with 'mongodb://' or 'mongodb+srv://'."
  }
}

# -----------------------------------------------------------------------------
# OPTIONAL VARIABLES (have sensible defaults)
# -----------------------------------------------------------------------------

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "restaurant-api"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be 'dev', 'staging', or 'prod'."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "West Europe"
}

variable "cpu_cores" {
  description = "Number of CPU cores for the container"
  type        = number
  default     = 1

  validation {
    condition     = var.cpu_cores >= 0.5 && var.cpu_cores <= 4
    error_message = "CPU cores must be between 0.5 and 4."
  }
}

variable "memory_gb" {
  description = "Memory in GB for the container"
  type        = number
  default     = 1.5

  validation {
    condition     = var.memory_gb >= 0.5 && var.memory_gb <= 16
    error_message = "Memory must be between 0.5 and 16 GB."
  }
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be DEBUG, INFO, WARNING, or ERROR."
  }
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# COMPUTED LOCALS
# -----------------------------------------------------------------------------

locals {
  # Resource naming convention: {project}-{environment}-{resource}
  resource_prefix = "${var.project_name}-${var.environment}"

  # Common tags applied to all resources
  common_tags = merge(
    {
      project     = var.project_name
      environment = var.environment
      managed_by  = "terraform"
      repository  = "restaurant-recommendation"
    },
    var.tags
  )
}
