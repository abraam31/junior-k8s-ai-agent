import json
import os
import sys
from .tools.client import load_kube_config
from .tools.workloads import get_pods_status, get_pods_logs
from .tools.events import get_events
from .tools.cluster import get_nodes_status
from .tools.schemas import TOOLS
from .prompts import SYSTEM_PROMPT
from .cache import make_key, set_entry, get_entry, init as init_cache
from anthropic import AnthropicBedrockMantle, Anthropic
import logging
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ANTHROPIC_MODEL = "claude-haiku-4-5"
BEDROCK_MODEL = "anthropic.claude-haiku-4-5"
MAX_TOKENS = 2048
MAX_TOOL_ROUNDS = 6

_client = None
_api_client = None
_model = None 

def build_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        logging.info("Using Anthropic API..")
        return Anthropic(api_key=api_key), ANTHROPIC_MODEL
    aws_region = os.getenv("AWS_REGION")
    if aws_region:
        logging.info(f"Using Bedrock in {aws_region}..")
        return AnthropicBedrockMantle(aws_region=aws_region), BEDROCK_MODEL
    logging.error("No API key or AWS region found. Set ANTHROPIC_API_KEY or AWS_REGION in the environment.")
    sys.exit(1)

def init():
    global _client, _api_client, _model, _prompt_version
    try:
        init_cache()
    except Exception as e:
        logging.warning(f"Failed to initialize cache: {e}")
    _client, _model = build_client()
    _api_client = load_kube_config()
    _prompt_version = get_prompt_version(_model)
    logging.info(f"Prompt version: {_prompt_version}")

def get_prompt_version(model: str):
    return hashlib.sha1(
        (SYSTEM_PROMPT + json.dumps(TOOLS, sort_keys=True) + model ).encode()
    ).hexdigest()[:8]

def answer(question) -> dict:
    """Answer a question using the Junior Agent"""
    first_message = f"Answer the question: {question}."
    diagnosis = run_junior(_client, _api_client, first_message)
    logging.info(f"Diagnosis: {diagnosis}")

    return diagnosis

def run_junior(client, api_client, first_message: str) -> dict:
    seen = {}
    def with_cache(entries):
        for entry in entries:
            key = make_key(entry, _prompt_version)
            hit = get_entry(key)
            identity = (entry["kind"], entry["name"], entry.get("container"))
            seen[identity] = (key, hit is not None)
            if hit:
                entry["cached_diagnosis"] = hit
        return entries 

    def pod_status_handler(inp):
        entries = get_pods_status(api_client, **inp)
        return with_cache(entries)

    def events_handler(inp):
        entries = get_events(api_client, **inp)
        return with_cache(entries)

    handlers = {
        "get_pods_status": pod_status_handler,
        "get_events": events_handler,
        "get_pods_logs": lambda inp: get_pods_logs(api_client, **inp),
        "get_nodes_status": lambda inp: get_nodes_status(api_client, **inp)
    }

    messages = [{"role": "user", "content": first_message}]

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        response = client.messages.create(
            model=_model,
            max_tokens=MAX_TOKENS,
            messages=messages,
            tools=TOOLS,
            system=SYSTEM_PROMPT,
            tool_choice={"type": "auto"},
        )
        print(response)
        logging.info(f"Round {round_num}: stop_reason={response.stop_reason}")

        tool_uses = [b for b in response.content if b.type == "tool_use"]

        for tool_use in tool_uses:
            if tool_use.name == "submit_diagnosis":
                logging.info(f" -> submit_diagnosis({json.dumps(tool_use.input)})")
                for d in tool_use.input.get("diagnosis", []):
                    identity = (d.get("kind"), d.get("name"), d.get("container"))
                    key, was_cached = seen.get(identity, (None, False))
                    if key and not was_cached:
                        set_entry(key, d)
                    d["cached"] = was_cached
                return {"diagnosis": tool_use.input.get("diagnosis", []), "summary": tool_use.input.get("summary", ""),"error": None}

        if response.stop_reason != "tool_use" or not tool_uses:
            text = "\n".join(b.text for b in response.content if b.type == "text")
            return {
                "error": f"no diagnosis was produced: stop_reason={response.stop_reason}. Exact error: {text}",
                "diagnosis": None,
            }

        tool_results = []

        for tu in tool_uses:
            logging.info(f" -> {tu.name}({json.dumps(tu.input)})")
            handler = handlers.get(tu.name)
            try:
                result = handler(tu.input)
                result_str = json.dumps(result) if not isinstance(result, str) else result
            except Exception as exc:
                logging.exception(f"Tool {tu.name} failed")
                result_str = json.dumps({"error": str(exc)})
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result_str})

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
        logging.info(f"Input token usage: {response.usage.input_tokens}. Output token usage: {response.usage.output_tokens}.")

    return {"diagnosis": None, "error": f"no diagnosis was concluded. Stop reason: {response.stop_reason}. Hit max tool rounds without a diagnosis."}

def main() -> None:
    init()
    namespace = sys.argv[1] if len(sys.argv) > 1 else "sandbox"

    first_message = f"Check pod status in namespace '{namespace}' and diagnose any problems you find."
    diagnosis = run_junior(_client, _api_client, first_message)

    logging.info("\nFinal diagnosis:")
    logging.info(json.dumps(diagnosis, indent=2))


if __name__ == "__main__":
    main()
