import json
import os
import sys
from .tools.k8s import load_kube_config, get_pods_status, get_pods_logs
from .tools.schemas import TOOLS
from .prompts import SYSTEM_PROMPT
import anthropic

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1024
MAX_TOOL_ROUNDS = 6

_client = None
_api_client = None

def init():
    global _client, _api_client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set Anthropic API key as ANTHROPIC_API_KEY in the environment: ", file=sys.stderr)
        sys.exit(1)
    _client = anthropic.Anthropic(api_key=api_key)
    _api_client = load_kube_config()

def answer(question) -> dict:
    """Answer a question using the Junior Agent"""
    first_message = f"Answer the question: {question}."
    diagnosis = run_junior(_client, _api_client, first_message)
    
    return diagnosis
    
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

    return {"diagnosis": [{"category": "unclear", "summary": "hit max tool rounds without a diagnosis", "escalate": True, "pod": None, "container": None}]}

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
