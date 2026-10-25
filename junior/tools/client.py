from kubernetes import client, config
from kubernetes.client import ApiClient
from pathlib import Path

KUBECONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "k8s-object" / "config"

def load_kube_config(kubeconfig: Path = KUBECONFIG_PATH) -> ApiClient:
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config(config_file=str(kubeconfig))
    return client.ApiClient()
