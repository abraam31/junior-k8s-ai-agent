from kubernetes.client import ApiClient, CoreV1Api
import json 

def get_nodes_status(api_client: ApiClient, node_name: str = None) -> list[dict]:
    core = CoreV1Api(api_client)
    nodes = [core.read_node(node_name)] if node_name else core.list_node().items
    node_status = []
    for node in nodes:
        taints = []
        issues = []
        name = node.metadata.name
        labels = node.metadata.labels
        node_taints = node.spec.taints if node.spec.taints else []
        status = node.status
        schedulable = True if not node.spec.unschedulable else False
        for taint in node_taints:
            actual=f"{taint.key}={taint.value}:{taint.effect}"
            taints.append(actual)
        for condition in status.conditions or []:
            if condition.type == "Ready":
                ready = condition.status
            healthy = "True" if condition.type == "Ready" else "False"
            if condition.status != healthy:
                issues.append({
                    "type": condition.type,
                    "status":condition.status,
                    "message": condition.message,
                    "reason": condition.reason,
                })

        node_status.append({
            "kind": "Node",
            "name": name,
            "labels": labels,
            "taints": taints,
            "ready": ready,
            "schedulable": schedulable,
            "issues": issues,
        })
    return node_status