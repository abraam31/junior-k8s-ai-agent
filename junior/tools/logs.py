from kubernetes import client
from kubernetes.client import ApiClient, CoreV1Api

def get_pods_logs(
    api_client: ApiClient,
    pod: str,
    container: str,
    namespace: str = "sandbox",
    previous: bool = False,
    tail_lines: int = 100,
) -> str:
    core = CoreV1Api(api_client)
    try:
        logs = core.read_namespaced_pod_log(
            pod,
            namespace,
            container=container,
            previous=previous,
            tail_lines=tail_lines,
        )
    except client.rest.ApiException as e:
        print(f"Error getting logs for {pod}/{container}: {e}")
        return "no logs available"
    return logs
