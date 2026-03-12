variable "cloud_provider" {
  description = "Target cloud provider: aws | azure | gcp"
  type        = string
  default     = "aws"

  validation {
    condition     = contains(["aws", "azure", "gcp"], var.cloud_provider)
    error_message = "cloud_provider must be one of: aws, azure, gcp."
  }
}

variable "project_name" {
  description = "Short name used to prefix all resources"
  type        = string
  default     = "psd-cloud"
}

variable "environment" {
  description = "Deployment environment: dev | staging | prod"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "Cloud region to deploy into (provider-specific format)"
  type        = string
  default     = "us-east-1"
}

# ─── Kubernetes Cluster ────────────────────────────────────────────────────

variable "k8s_node_count" {
  description = "Number of worker nodes in the Kubernetes cluster"
  type        = number
  default     = 3
}

variable "k8s_node_size" {
  description = "VM/instance type for worker nodes (provider-specific)"
  type        = string
  default     = "t3.medium"
}

variable "k8s_version" {
  description = "Kubernetes version to provision"
  type        = string
  default     = "1.29"
}

# ─── Database ──────────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "Database instance size (provider-specific)"
  type        = string
  default     = "db.t3.micro"
}

variable "db_storage_gb" {
  description = "Allocated storage for PostgreSQL in GiB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "psd_cloud"
}

variable "db_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "psd"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

# ─── Object Storage ────────────────────────────────────────────────────────

variable "reports_bucket_name" {
  description = "Name of the object storage bucket for scan reports"
  type        = string
  default     = "psd-cloud-reports"
}
