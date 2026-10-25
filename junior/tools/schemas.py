TOOLS = [
    {
        "name": "get_pods_status",
        "description": "Check status of all pods in a given namespace. It returns 2 types of categories of pods: problematic pods and flagged pods. Problematic pods are pods that have problems ar the current moment and needs to be looked at. Flagged pods are pods that running fine but last exit code is not 0 and needs to be looked at.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "the namespace to check the status of pods"},
            },
            "required": []
        }
    },
    {
        "name": "get_pods_logs",
        "description": "Get logs of a specific pod and container. You can use previous=True to get logs on the previous run, mainly for the category of flagged pods. The returned logs are formatted as a string. Tail lines is the number of lines to return, default is 100.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod": {
                    "type": "string",
                    "description": "the pod to get the logs of"
                },
                "container": {
                    "type": "string",
                    "description": "the container to get the logs of"
                },
                "namespace": {
                    "type": "string",
                    "description": "the namespace to get the logs of"
                },
                "previous": {
                    "type": "boolean",
                    "description": "whether to get logs on the previous run, mainly for the category of flagged pods"
                },
                "tail_lines": {
                    "type": "integer",
                    "description": "the number of lines to return, default is 100"
                },
            },
            "required": ["pod", "container", "namespace"]
        }
    },
    { 
        "name": "get_events",
        "description": "Get events of a given namespace. It returns a dictionary of events with the event message as the key and the values is a tuple of (Kubernetes Object kind/name,number of occurences of events, seconds since first occurrence, seconds since last occurrence).",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "the namespace to get the events of"
                }
            },
            "required": [],
        }
    },
    {
        "name": "get_nodes_status",
        "description": "Get status of all nodes in the cluster. It returns a list of nodes with their: name, labels, taints, readiness, schedulable, and issues if present. Usually don't need this tool unless either there is explicit question about nodes status in the cluster, or the pods issues is like stuck in pending state, or any issue that might be related to nodes which should be explicit and clear.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_name": {
                    "type": "string",
                    "description": "the name of a specific node to get its status, otherwise all nodes will be returned"
                }
            },
            "required": [],
        }
    },
    {
        "name": "submit_diagnosis",
        "description": "Submit your diagnosis for the found issues, whether it is a pod issue or a general issue like PVC or RBAC or else. It returns a structured verdict.",
        "input_schema": {
            "type": "object",
            "properties": {
                "diagnosis": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string", 
                                "enum": ["k8s_issue", "app_issue", "unclear"]
                            },
                            "summary": {"type": "string", "description": "Plain-language summary of what's wrong and why"},
                            "kind": {
                                "type": "string",
                                "description": "Kubernetes kind of the object diagnosed, e.g. Pod, ReplicaSet, PersistentVolumeClaim"
                            },
                            "name": {"type": "string", "description": "name of the object diagnosed, e.g. the pod name, or the PVC name"},
                            "container": {"type": "string", "description": "the container diagnosed in case the kind is Pod"},
                        },
                        "required": ["category", "summary", "kind", "name"],
                        "additionalProperties": False,
                    }
                },
                "summary": {"type": "string", "description": "1-3 sentence answer to the question, also when no issues were found, e.g. 'Both nodes are Ready and schedulable; no node issues.'"},
            },
            "required": ["diagnosis", "summary"],
        },
    },
]
