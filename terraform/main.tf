terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.35.1"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

###############################################
# (NO Tekton CRDs block) -- We assume you run:
#   kubectl apply -f https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml
# outside Terraform to install Tekton CRDs.
###############################################

###############################################
# MinIO, Prometheus, Grafana, etc.
###############################################
resource "kubernetes_manifest" "minio_deployment" {
  manifest = yamldecode(file("${path.module}/../kubernetes/minio-deployment.yaml"))
}

resource "kubernetes_manifest" "minio_service" {
  manifest = yamldecode(file("${path.module}/../kubernetes/minio-service.yaml"))
}

resource "kubernetes_manifest" "prometheus_deployment" {
  manifest = yamldecode(file("${path.module}/../monitoring/prometheus-deployment.yaml"))
}

resource "kubernetes_manifest" "prometheus_service" {
  manifest = yamldecode(file("${path.module}/../monitoring/prometheus-service.yaml"))
}

resource "kubernetes_manifest" "grafana_deployment" {
  manifest = yamldecode(file("${path.module}/../monitoring/grafana-deployment.yaml"))
}

resource "kubernetes_manifest" "grafana_service" {
  manifest = yamldecode(file("${path.module}/../monitoring/grafana-service.yaml"))
}

