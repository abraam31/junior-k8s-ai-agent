from .client import ensure_namespace
from kubernetes.client import ApiClient, CoreV1Api
import re
from datetime import datetime, timezone

def get_events(api_client: ApiClient, namespace: str = "sandbox") -> list[dict]:
    ensure_namespace(api_client, namespace)
    core = CoreV1Api(api_client)
    events = core.list_namespaced_event(namespace=namespace)
    now = datetime.now(timezone.utc)
    results = []
    seen = set()

    for event in events.items:
        if event.type == "Normal":
            continue 
        obj = event.involved_object
        container = None
        if obj.field_path:
            match = re.search(r"\{(.+)\}", obj.field_path)
            container = match.group(1) if match else None
        key = (obj.kind, obj.name, container, event.reason)
        if key in seen:
            continue
        seen.add(key)
        first = int((now - event.first_timestamp).total_seconds()) if event.first_timestamp else 0
        last = int((now - event.last_timestamp).total_seconds()) if event.last_timestamp else 0
        results.append({
            "name": obj.name,
            "kind": obj.kind,
            "namespace": obj.namespace,
            "container": container,
            "reason": event.reason,
            "message": event.message,
            "category": "event",
            "first_seen_seconds_ago": first,
            "last_seen_seconds_ago": last,
            "num_times_seen": event.count,

        })
    return results
