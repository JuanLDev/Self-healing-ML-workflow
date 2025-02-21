# Tiltfile

###########################################################
# 1) Docker builds for each script
###########################################################
docker_build(
    "juanlugodev/data-fetch",
    "./data-fetch",
    dockerfile="./data-fetch/Dockerfile.fetch",
    live_update=[
        sync("./data-fetch", "/app"),
        run("pip install --no-cache-dir -r requirements_fetch.txt", trigger=["requirements_fetch.txt"]),
    ],
)

docker_build(
    "juanlugodev/data-ingestion",
    "./data-ingestion",
    dockerfile="./data-ingestion/Dockerfile.ingestion",
    live_update=[
        sync("./data-ingestion", "/app"),
        run("pip install --no-cache-dir -r requirements_ingestion.txt", trigger=["requirements_ingestion.txt"]),
    ],
)

docker_build(
    "juanlugodev/model-training",
    "./model-training",
    dockerfile="./model-training/Dockerfile.training",
    live_update=[
        sync("./model-training", "/app"),
        run("pip install --no-cache-dir -r requirements_training.txt", trigger=["requirements_training.txt"]),
    ],
)

###########################################################
# 2) Apply all Tekton + MinIO YAML via k8s_yaml
###########################################################
k8s_yaml([
    # MinIO (assuming you have these YAMLs in `kubernetes/`)
    "kubernetes/minio-deployment.yaml",
    "kubernetes/minio-service.yaml",

    # Tekton tasks
    "ml-pipeline/tekton_task_datafetch.yaml",
    "ml-pipeline/tekton_task_dataingestion.yaml",
    "ml-pipeline/tekton_task_modeltraining.yaml",

    # Tekton pipeline & pipelineRun
    "ml-pipeline/tekton_pipeline.yaml",
    "ml-pipeline/tekton_pipelinerun.yaml",
])
