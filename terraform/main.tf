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
# StorageClass, PV, PVC for MinIO
###############################################

# 1) StorageClass
resource "kubernetes_manifest" "minio_storageclass" {
  manifest = yamldecode(file("${path.module}/../kubernetes/minio-storageclass.yaml"))
}




###############################################
# MinIO Deployment & Service
###############################################
resource "kubernetes_manifest" "minio_deployment" {
  manifest = yamldecode(file("${path.module}/../kubernetes/minio-deployment.yaml"))

  lifecycle {
    ignore_changes = [
      # If your older provider lumps all labels into a single map:
      "object.metadata[0].labels",
      "object.spec.template.metadata[0].labels",
    ]
  }
}

resource "kubernetes_manifest" "minio_service" {
  depends_on = [kubernetes_manifest.minio_deployment]
  manifest   = yamldecode(file("${path.module}/../kubernetes/minio-service.yaml"))
}

###############################################
# Prometheus / Grafana Deploy/Service
###############################################
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
