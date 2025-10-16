# MemMachine-in-a-Box Terraform Configuration
# Complete infrastructure deployment for MemMachine on GCP

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
}

# Variables for customization
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "openai_api_key" {
  description = "OpenAI API Key for MemMachine"
  type        = string
  sensitive   = true
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# GKE Cluster for MemMachine
resource "google_container_cluster" "memmachine_cluster" {
  name     = "memmachine-cluster"
  location = var.region

  initial_node_count = 3

  node_config {
    machine_type = "n1-standard-2"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }

  # Enable required features
  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }
    http_load_balancing {
      disabled = false
    }
  }
}

# Cloud SQL for PostgreSQL with pgvector
resource "google_sql_database_instance" "postgres" {
  name             = "memmachine-postgres"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-custom-2-7680"

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    backup_configuration {
      enabled = true
      start_time = "03:00"
    }

    ip_configuration {
      ipv4_enabled    = true
      private_network = google_compute_network.vpc.id

      authorized_networks {
        name  = "allow-k8s"
        value = "0.0.0.0/0"
      }
    }
  }

  deletion_protection = false
}

# PostgreSQL Database
resource "google_sql_database" "memmachine_db" {
  name     = "memmachine"
  instance = google_sql_database_instance.postgres.name
}

# PostgreSQL User
resource "google_sql_user" "postgres_user" {
  name     = "memmachine"
  instance = google_sql_database_instance.postgres.name
  password = random_password.postgres_password.result
}

# Random password for PostgreSQL
resource "random_password" "postgres_password" {
  length  = 32
  special = true
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "memmachine-vpc"
  auto_create_subnetworks = true
}

# Secret Manager for API keys
resource "google_secret_manager_secret" "openai_key" {
  secret_id = "openai-api-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "openai_key_version" {
  secret = google_secret_manager_secret.openai_key.id
  secret_data = var.openai_api_key
}

# Configure kubectl and helm providers
data "google_client_config" "default" {}

data "google_container_cluster" "memmachine" {
  name     = google_container_cluster.memmachine_cluster.name
  location = google_container_cluster.memmachine_cluster.location
}

provider "kubernetes" {
  host  = "https://${data.google_container_cluster.memmachine.endpoint}"
  token = data.google_client_config.default.access_token

  cluster_ca_certificate = base64decode(
    data.google_container_cluster.memmachine.master_auth[0].cluster_ca_certificate,
  )
}

provider "helm" {
  kubernetes {
    host  = "https://${data.google_container_cluster.memmachine.endpoint}"
    token = data.google_client_config.default.access_token

    cluster_ca_certificate = base64decode(
      data.google_container_cluster.memmachine.master_auth[0].cluster_ca_certificate,
    )
  }
}

# Neo4j Helm deployment
resource "helm_release" "neo4j" {
  name       = "neo4j"
  repository = "https://neo4j.github.io/helm-charts"
  chart      = "neo4j"
  namespace  = "memmachine"

  create_namespace = true

  values = [
    <<-EOT
    neo4j:
      password: ${random_password.neo4j_password.result}
      edition: "community"

    volumes:
      data:
        size: 10Gi

    resources:
      cpu: "1000m"
      memory: "2Gi"
    EOT
  ]
}

# Random password for Neo4j
resource "random_password" "neo4j_password" {
  length  = 32
  special = true
}

# Prometheus for monitoring
resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = "monitoring"

  create_namespace = true

  set {
    name  = "grafana.adminPassword"
    value = random_password.grafana_password.result
  }
}

# Random password for Grafana
resource "random_password" "grafana_password" {
  length  = 16
  special = true
}

# MemMachine Kubernetes deployment
resource "kubernetes_namespace" "memmachine" {
  metadata {
    name = "memmachine"
  }
}

resource "kubernetes_deployment" "memmachine" {
  metadata {
    name      = "memmachine"
    namespace = kubernetes_namespace.memmachine.metadata[0].name
  }

  spec {
    replicas = 3

    selector {
      match_labels = {
        app = "memmachine"
      }
    }

    template {
      metadata {
        labels = {
          app = "memmachine"
        }
      }

      spec {
        container {
          name  = "memmachine"
          image = "ghcr.io/memmachine/memmachine:latest"

          env {
            name  = "POSTGRES_HOST"
            value = google_sql_database_instance.postgres.public_ip_address
          }

          env {
            name  = "POSTGRES_USER"
            value = google_sql_user.postgres_user.name
          }

          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.db_credentials.metadata[0].name
                key  = "postgres-password"
              }
            }
          }

          env {
            name  = "NEO4J_HOST"
            value = "neo4j.memmachine.svc.cluster.local"
          }

          env {
            name = "NEO4J_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.db_credentials.metadata[0].name
                key  = "neo4j-password"
              }
            }
          }

          env {
            name = "OPENAI_API_KEY"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.api_keys.metadata[0].name
                key  = "openai-key"
              }
            }
          }

          port {
            container_port = 8080
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 30
            period_seconds        = 10
          }

          readiness_probe {
            http_get {
              path = "/health/ready"
              port = 8080
            }
            initial_delay_seconds = 10
            period_seconds        = 5
          }

          resources {
            limits = {
              cpu    = "1000m"
              memory = "2Gi"
            }
            requests = {
              cpu    = "500m"
              memory = "1Gi"
            }
          }
        }
      }
    }
  }
}

# Kubernetes secrets
resource "kubernetes_secret" "db_credentials" {
  metadata {
    name      = "db-credentials"
    namespace = kubernetes_namespace.memmachine.metadata[0].name
  }

  data = {
    postgres-password = random_password.postgres_password.result
    neo4j-password   = random_password.neo4j_password.result
  }
}

resource "kubernetes_secret" "api_keys" {
  metadata {
    name      = "api-keys"
    namespace = kubernetes_namespace.memmachine.metadata[0].name
  }

  data = {
    openai-key = var.openai_api_key
  }
}

# Service to expose MemMachine
resource "kubernetes_service" "memmachine" {
  metadata {
    name      = "memmachine"
    namespace = kubernetes_namespace.memmachine.metadata[0].name
  }

  spec {
    selector = {
      app = "memmachine"
    }

    port {
      port        = 80
      target_port = 8080
    }

    type = "LoadBalancer"
  }
}

# Ingress for external access
resource "kubernetes_ingress_v1" "memmachine" {
  metadata {
    name      = "memmachine"
    namespace = kubernetes_namespace.memmachine.metadata[0].name

    annotations = {
      "nginx.ingress.kubernetes.io/rewrite-target" = "/"
    }
  }

  spec {
    rule {
      http {
        path {
          path = "/"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service.memmachine.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }
}

# Outputs
output "memmachine_url" {
  value       = kubernetes_service.memmachine.status[0].load_balancer[0].ingress[0].ip
  description = "MemMachine API endpoint"
}

output "grafana_url" {
  value       = "http://${kubernetes_service.grafana.status[0].load_balancer[0].ingress[0].ip}"
  description = "Grafana monitoring dashboard"
}

output "postgres_connection" {
  value       = "${google_sql_database_instance.postgres.public_ip_address}:5432"
  description = "PostgreSQL connection endpoint"
}

output "grafana_password" {
  value       = random_password.grafana_password.result
  sensitive   = true
  description = "Grafana admin password"
}

# Service for Grafana access
resource "kubernetes_service" "grafana" {
  metadata {
    name      = "grafana-external"
    namespace = "monitoring"
  }

  spec {
    selector = {
      "app.kubernetes.io/name" = "grafana"
    }

    port {
      port        = 80
      target_port = 3000
    }

    type = "LoadBalancer"
  }
}