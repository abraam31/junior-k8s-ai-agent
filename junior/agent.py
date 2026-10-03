import json
import os
import sys
from .tools.k8s import load_kube_config, get_pods_status, get_pods_logs
from .tools.schemas import TOOLS
from .prompts import SYSTEM_PROMPT
from anthropic import AnthropicBedrockMantle, Anthropic
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ANTHROPIC_MODEL = "claude-haiku-4-5"
BEDROCK_MODEL = "anthropic.claude-haiku-4-5"
MAX_TOKENS = 1024
MAX_TOOL_ROUNDS = 6

_client = None
_api_client = None
_model = None 

def build_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        logging.info("Using Anthropic API..")
        return Anthropic(api_key=api_key), ANTHROPIC_MODEL
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    if aws_region:
        logging.info(f"Using Bedrock in {aws_region}..")
        return AnthropicBedrockMantle(aws_region=aws_region), BEDROCK_MODEL
    logging.error("No API key or AWS region found. Set ANTHROPIC_API_KEY or AWS_REGION in the environment.")
    sys.exit(1)

def init():
    global _client, _api_client, _model
    aws_region = os.getenv("AWS_REGION")
    _client, _model = build_client()
    _api_client = load_kube_config()

def answer(question) -> dict:
    """Answer a question using the Junior Agent"""
    first_message = f"Answer the question: {question}."
    diagnosis = run_junior(_client, _api_client, first_message)
    
    return diagnosis
    
def run_junior(client, api_client, first_message: str) -> dict:
    handlers = {
        "get_pods_status": lambda inp: get_pods_status(api_client, **inp),
        "get_pods_logs": lambda inp: get_pods_logs(api_client, **inp),
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

        logging.info(f"Round {round_num}: stop_reason={response.stop_reason}")

        tool_uses = [b for b in response.content if b.type == "tool_use"]

        for tool_use in tool_uses:
            if tool_use.name == "submit_diagnosis":
                logging.info(f" -> submit_diagnosis({json.dumps(tool_use.input)})")
                return {"diagnosis": tool_use.input.get("diagnosis", {}), "error": None}

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
                result_str = json.dumps({"error": str(exc)})
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result_str})

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return {"diagnosis": None, "error": f"no diagnosis was concluded. Stop reason: {response.stop_reason}. Hit max tool rounds without a diagnosis."}

def main() -> None:
    init()
    namespace = sys.argv[1] if len(sys.argv) > 1 else "sandbox"

    first_message = f"Check pod status in namespace '{namespace}' and diagnose any problems you find."
    diagnosis = run_junior(client, api_client, first_message)

    logging.info("\nFinal diagnosis:")
    logging.info(json.dumps(diagnosis, indent=2))


if __name__ == "__main__":
    main()
