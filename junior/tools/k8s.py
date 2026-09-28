from kubernetes import client, config
from kubernetes.client import ApiClient, CoreV1Api
from pathlib import Path
import argparse
import re

KUBECONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "k8s-object" / "config"

def load_kube_config(kubeconfig: Path = KUBECONFIG_PATH) -> ApiClient:
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config(config_file=str(kubeconfig))
    return client.ApiClient()

def check_container_status(container: client.V1ContainerStatus) ->  tuple[str, str, str, bool]:
    problematic = False
    name = container.name
    if container.state.waiting:
        reason = container.state.waiting.reason
        if reason in ["ContainerCreating","PodInitializing"]:
            return name, None, None, False
        else:
            message = container.state.waiting.message
            problematic = True
            return name, reason, message, problematic
    if container.state.terminated:
        code = container.state.terminated.exit_code
        if code != 0:
            reason = container.state.terminated.reason
            message = container.state.terminated.message or ""
            message += f" ExitCode: {code}"
            problematic = True
            return name, reason, message, problematic
    return name, None, None, False

def check_last_state(container: client.V1ContainerStatus) -> tuple[str, str, str, bool]:
    flagged = False
    if container.state.running:
        name = container.name
        restart_count = container.restart_count
        if restart_count > 0:
            if container.last_state.terminated:
                exit_code = container.last_state.terminated.exit_code
                reason = container.last_state.terminated.reason
                message = container.last_state.terminated.message or ""
                message += f" ExitCode: {exit_code}"
                flagged = True
                return name, reason, message, flagged
    return None, None, None, flagged

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

def get_pods_status(api_client: ApiClient, namespace: str = "sandbox") -> list[dict]:
    results = []
    problematic_owners = set()
    flagged_owners = set()
    core = CoreV1Api(api_client)
    pods = core.list_namespaced_pod(namespace=namespace)
    for pod in pods.items:
        containers = pod.status.container_statuses or []
        spec_by_name = {c.name: c for c in (pod.spec.containers or [])}
        owner_refs = pod.metadata.owner_references
        owner = pod_owner(owner_refs[0]) if owner_refs else None
        for container in containers:
            spec_container = spec_by_name.get(container.name)
            mounts = {mount.name for mount in (container.volume_mounts or [])}
            envs = spec_container.env if spec_container else []
            env_from = spec_container.env_from if spec_container else []
            config_maps, secrets = extract_secrets_and_config_maps(mounts, pod.spec.volumes, envs, env_from)
            cname_p, reason_p, message_p, problematic = check_container_status(container)
            if problematic:
                if owner and owner in problematic_owners:
                    continue
                results.append({
                    "pod": pod.metadata.name,
                    "namespace": namespace,
                    "container": cname_p,
                    "reason": reason_p,
                    "message": message_p,
                    "category": "problematic",
                    "owner": owner,
                    "config_maps": config_maps,
                    "secrets": secrets,
                })
                if owner:
                    problematic_owners.add(owner)
            cname_f, reason_f, message_f, flagged = check_last_state(container)
            if flagged:
                if owner and owner in flagged_owners:
                    continue
                results.append({
                    "pod": pod.metadata.name,
                    "namespace": namespace,
                    "container": cname_f,
                    "reason": reason_f,
                    "message": message_f,
                    "category": "flagged",
                    "owner": owner,
                    "config_maps": config_maps,
                    "secrets": secrets,
                })
                if owner:
                    flagged_owners.add(owner)
    return results

def pod_owner(owner_ref: client.V1OwnerReference) -> str:
    type = owner_ref.kind
    name = owner_ref.name
    owner = re.sub(r'-[0-9]+$', '', name)
    return f"{type}/{owner}"

def extract_secrets_and_config_maps(mounts, volumes, envs, env_froms):
    secrets = set()
    config_maps = set()
    for vol in volumes or []:
        if vol.name not in mounts:
            continue
        if vol.secret:
            secrets.add(vol.secret.secret_name)
        if vol.config_map:
            config_maps.add(vol.config_map.name)
    for env in envs or []:
        if env.value_from and env.value_from.secret_key_ref:
            secrets.add(env.value_from.secret_key_ref.name)
        if env.value_from and env.value_from.config_map_key_ref:
            config_maps.add(env.value_from.config_map_key_ref.name)
    for env_from in env_froms or []:
        if env_from.secret_ref:
            secrets.add(env_from.secret_ref.name)
        if env_from.config_map_ref:
            config_maps.add(env_from.config_map_ref.name)
    return sorted(config_maps), sorted(secrets)

def main(namespace: str, tail_lines: int, kubeconfig: Path) -> None:
    api_client = load_kube_config(kubeconfig)
    results = get_pods_status(api_client, namespace)
    for result in results:
        print(result)

    # if problems:
    #     for pod, containers in problematic_pods.items():
    #         for cname, reason, message in containers:
    #             logs = get_pods_logs(api_client, pod, cname, namespace=namespace, tail_lines=tail_lines)
    #             print(f"Problematic {pod}/{cname} ({reason}): {message}\n{logs}")
    # if flags:
    #     for pod, containers in flagged_pods.items():
    #         for cname, reason, message in containers:
    #             logs = get_pods_logs(api_client, pod, cname, namespace=namespace, previous=True, tail_lines=tail_lines)
    #             print(f"Flagged {pod}/{cname} ({reason}): {message}\n{logs}")
    # if not problems and not flags:
    #     print("No problems found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", type=str, default="sandbox")
    parser.add_argument("--tail-lines", type=int, default=100)
    parser.add_argument("--kubeconfig", type=Path, default=KUBECONFIG_PATH)
    args = parser.parse_args()
    main(args.namespace, args.tail_lines, args.kubeconfig)