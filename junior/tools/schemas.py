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
        "name": "submit_diagnosis",
        "description": "Submit your diagnosis for the given pods. It returns a structured verdict.",
        "input_schema": {
            "type": "object",
            "properties": {
                "diagnosis": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "enum": ["k8s_issue", "unclear"]},
                            "summary": {"type": "string", "description": "Plain-language summary of what's wrong and why"},
                            "cached": {"type": "boolean", "description": "True if this diagnosis is cached"},
                            "pod": {"type": "string", "description": "the pod diagnosed"},
                            "container": {"type": "string", "description": "the container diagnosed"},
                        }
                    }
                }
            },
            "required": ["diagnosis"],
        },
    },
]
