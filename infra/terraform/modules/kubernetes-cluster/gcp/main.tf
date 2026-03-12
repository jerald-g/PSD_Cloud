variable "cluster_name"  { type = string }
variable "region"        { type = string }
variable "node_count"    { type = number }
variable "machine_type"  { type = string }
variable "k8s_version"   { type = string }

resource "google_container_cluster" "main" {
  name             = var.cluster_name
  location         = var.region
  min_master_version = var.k8s_version
  # Minimal default node pool (required); actual workloads use separate pool
  remove_default_node_pool = true
  initial_node_count       = 1
}

resource "google_container_node_pool" "primary" {
  name       = "${var.cluster_name}-primary"
  cluster    = google_container_cluster.main.name
  location   = var.region
  node_count = var.node_count

  node_config {
    machine_type = var.machine_type
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
  }
}

output "cluster_endpoint" { value = google_container_cluster.main.endpoint }
output "cluster_name"     { value = google_container_cluster.main.name }
