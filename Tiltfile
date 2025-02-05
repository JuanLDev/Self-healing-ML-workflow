docker_build("ml-workflow", ".", live_update=[
    sync(".", "/app"),
    run("pip install -r requirements.txt", trigger=["requirements.txt"]),
])
k8s_yaml("kubernetes/ml-workflow-deployment.yaml")
k8s_resource("ml-workflow", port_forwards=8081)
