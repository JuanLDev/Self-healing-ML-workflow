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
      object.metadata[0].labels,
      object.spec.template.metadata[0].labels,
    ]
  }
}

###############################################
# Ensure Tekton Namespace Exists via `kubectl`
###############################################
resource "null_resource" "ensure_tekton_namespace" {
  provisioner "local-exec" {
    command = <<EOT
      kubectl get namespace tekton-pipelines || kubectl create namespace tekton-pipelines
    EOT
  }
}

###############################################
# Install Tekton Pipelines via `kubectl apply`
###############################################
resource "null_resource" "install_tekton" {
  depends_on = [null_resource.ensure_tekton_namespace]

  provisioner "local-exec" {
    command = <<EOT
      kubectl apply -f https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml
    EOT
  }
}

###############################################
# Tekton Pipeline, Tasks, and PipelineRun
###############################################
resource "null_resource" "apply_tekton_pipeline" {
  depends_on = [null_resource.install_tekton]

  provisioner "local-exec" {
    command = "kubectl apply -f ${path.module}/../ml-pipeline/tekton_pipeline.yaml"
  }
}

resource "null_resource" "apply_tekton_pipelinerun" {
  depends_on = [null_resource.apply_tekton_pipeline]

  provisioner "local-exec" {
    command = "kubectl apply -f ${path.module}/../ml-pipeline/tekton_pipelinerun.yaml"
  }
}

resource "null_resource" "apply_tekton_task_datafetch" {
  depends_on = [null_resource.apply_tekton_pipeline]

  provisioner "local-exec" {
    command = "kubectl apply -f ${path.module}/../ml-pipeline/tekton_task_datafetch.yaml"
  }
}

resource "null_resource" "apply_tekton_task_dataingestion" {
  depends_on = [null_resource.apply_tekton_pipeline]

  provisioner "local-exec" {
    command = "kubectl apply -f ${path.module}/../ml-pipeline/tekton_task_dataingestion.yaml"
  }
}

resource "null_resource" "apply_tekton_task_modeltraining" {
  depends_on = [null_resource.apply_tekton_pipeline]

  provisioner "local-exec" {
    command = "kubectl apply -f ${path.module}/../ml-pipeline/tekton_task_modeltraining.yaml"
  }
}

###############################################
# MinIO Service
###############################################
resource "kubernetes_manifest" "minio_service" {
  depends_on = [kubernetes_manifest.minio_deployment]
  manifest   = yamldecode(file("${path.module}/../kubernetes/minio-service.yaml"))
}

###############################################
# Prometheus / Grafana Deployment & Service
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
