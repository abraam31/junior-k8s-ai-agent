import json
import os
import sys 
from k8s_tools import load_kube_config, get_pods_status, get_pods_logs
import anthropic

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1024
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """You are Junior, a read-only kubernetes trige agent. 

You have three tools: 
- get_pods_status: it checks status of all pods in a given namespace. It either returns a list of problematic pods which have problems at the current moment, or flagged pods that running fine but last exit code is not 0 and needs to be looked at.
- get_pods_logs: it returns logs of a specific pod and container. You can use previous=True to get logs on the previous run, mainly for the category of flagged pods. The returned logs are formatted as a string.
- submit_diagnosis: end your investigation with a structured verdict

You never take any write actions. You are always read-only, never modify any things.

Investigate using get_logs whenever the status is not enough to identify the root cause.
You must always end by calling submit_diagnosis, never by just writing a text answer.
Set escalate=true only if the root cause looks like an application/code issue rather
than something you can fully explain from Kubernetes-level data (resources, config,
image pull, node issues).""" 

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
                "category": {"type": "string", "enum": ["k8s_issue", "unclear"]},
                "summary": {"type": "string", "description": "Plain-language summary of what's wrong and why"},
                "escalate": {"type": "boolean", "description": "True if this needs deeper code-level investigation"},
            },
            "required": ["category", "summary", "escalate"],
        },
    },
]

def run_junior(client: anthropic.Anthropic, api_client, first_message: str) -> dict:
    handlers = {
        "get_pods_status": lambda inp: get_pods_status(api_client, **inp), 
        "get_pods_logs": lambda inp: get_pods_logs(api_client, **inp),
    }

    messages = [{"role": "user", "content": first_message}]

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=messages,
            tools=TOOLS,
            system=SYSTEM_PROMPT,
            tool_choice={"type": "auto"},
        )
        
        print(f"Round {round_num}: stop_reason={response.stop_reason}")

        tool_uses = [b for b in response.content if b.type == "tool_use"]

        for tool_use in tool_uses:
            if tool_use.name == "submit_diagnosis":
                print(f" -> submit_diagnosis({json.dumps(tool_use.input)})")
                return tool_use.input
        
        if response.stop_reason != "tool_use" or not tool_uses:
            text = "\n".join(b.text for b in response.content if b.type == "text")
            return {
                "error": f"no diagnosis was produced: stop_reason={response.stop_reason}",
                "raw_text": text,
            }
        
        tool_results = []

        for tu in tool_uses:
            print(f" -> {tu.name}({json.dumps(tu.input)})")
            handler = handlers.get(tu.name)
            try:
                result = handler(tu.input)
                result_str = json.dumps(result) if not isinstance(result, str) else result
            except Exception as exc:
                result_str = json.dumps({"error": str(exc)})
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result_str})
        
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return {"category": "unclear", "summary": "hit max tool rounds without a diagnosis", "escalate": False}

def main() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set Anthropic API key as ANTHROPIC_API_KEY in the environment: ", file=sys.stderr)
        sys.exit(1)
    
    namespace = sys.argv[1] if len(sys.argv) > 1 else "sandbox"

    client = anthropic.Anthropic(api_key=api_key)
    api_client = load_kube_config()

    first_message = f"Check pod status in namespace '{namespace}' and diagnose any problems you find."
    diagnosis = run_junior(client, api_client, first_message)

    print("\nFinal diagnosis:")
    print(json.dumps(diagnosis, indent=2))


if __name__ == "__main__":
    main()            