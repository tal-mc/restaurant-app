# =============================================================================
# OUTPUTS.TF - Output Values
# =============================================================================
# These values are displayed after terraform apply and can be used by:
# - CI/CD pipelines (for smoke tests)
# - Other Terraform configurations
# - Documentation
# =============================================================================

# -----------------------------------------------------------------------------
# PRIMARY OUTPUTS
# -----------------------------------------------------------------------------

output "api_url" {
  description = "Base URL for the API (use for health checks)"
  value       = "http://${azurerm_container_group.api.fqdn}:8080"
}

output "rest_endpoint" {
  description = "Full URL for the /rest endpoint"
  value       = "http://${azurerm_container_group.api.fqdn}:8080/rest"
}

output "health_endpoint" {
  description = "Full URL for the /health endpoint"
  value       = "http://${azurerm_container_group.api.fqdn}:8080/health"
}

# -----------------------------------------------------------------------------
# RESOURCE DETAILS
# -----------------------------------------------------------------------------

output "fqdn" {
  description = "Fully qualified domain name of the container"
  value       = azurerm_container_group.api.fqdn
}

output "ip_address" {
  description = "Public IP address of the container"
  value       = azurerm_container_group.api.ip_address
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "container_name" {
  description = "Name of the container instance"
  value       = azurerm_container_group.api.name
}

# -----------------------------------------------------------------------------
# DEPLOYMENT INFO
# -----------------------------------------------------------------------------

output "docker_image" {
  description = "Docker image currently deployed"
  value       = var.docker_image
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# -----------------------------------------------------------------------------
# CURL EXAMPLES (for quick testing)
# -----------------------------------------------------------------------------

output "example_commands" {
  description = "Example curl commands to test the API"
  value = <<-EOT
    
    # Health check
    curl "http://${azurerm_container_group.api.fqdn}:8080/health"
    
    # Query examples
    curl "http://${azurerm_container_group.api.fqdn}:8080/rest?query=italian"
    curl "http://${azurerm_container_group.api.fqdn}:8080/rest?query=vegetarian%20asian"
    curl "http://${azurerm_container_group.api.fqdn}:8080/rest?query=steakhouse%20between%2010:00%20and%2022:00"
    
  EOT
}
