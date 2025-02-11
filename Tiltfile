# Tiltfile

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

k8s_yaml("ml-pipeline/tekton-ml-pipeline.yaml")
# Possibly any other YAML you have
