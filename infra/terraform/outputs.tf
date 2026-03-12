output "cluster_endpoint" {
  description = "Kubernetes API server endpoint"
  value = coalesce(
    try(module.aws_cluster[0].cluster_endpoint, ""),
    try(module.azure_cluster[0].cluster_endpoint, ""),
    try(module.gcp_cluster[0].cluster_endpoint, ""),
  )
}

output "db_endpoint" {
  description = "PostgreSQL connection endpoint"
  sensitive   = true
  value = coalesce(
    try(module.aws_database[0].endpoint, ""),
    try(module.azure_database[0].endpoint, ""),
    try(module.gcp_database[0].endpoint, ""),
  )
}

output "reports_bucket" {
  description = "Object storage bucket / container name for scan reports"
  value = coalesce(
    try(module.aws_storage[0].bucket_name, ""),
    try(module.azure_storage[0].container_name, ""),
    try(module.gcp_storage[0].bucket_name, ""),
  )
}

output "kubeconfig_command" {
  description = "CLI command to configure kubectl for the provisioned cluster"
  value = var.cloud_provider == "aws" ? (
    "aws eks update-kubeconfig --name ${var.project_name}-${var.environment} --region ${var.region}"
  ) : var.cloud_provider == "azure" ? (
    "az aks get-credentials --resource-group ${var.project_name}-${var.environment}-rg --name ${var.project_name}-${var.environment}"
  ) : (
    "gcloud container clusters get-credentials ${var.project_name}-${var.environment} --region ${var.region}"
  )
}
