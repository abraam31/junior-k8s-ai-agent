import yaml
import requests 
import re 
import sys

BASE_URL = "http://127.0.0.1:8000/ask"
THRESHOLD = 90  # percent of cases that must pass

def load_cases(file: str = "eval/cases.yaml") -> list[dict]:
    with open(file, "r") as f:
        cases = yaml.safe_load(f)
    return cases

def expected_results(case: str) -> list[dict]:
    return case.get("expected", [])

def agent_results(case: dict) -> tuple[int, list[dict]]:
    results = []
    response = requests.post(BASE_URL, json={"question": case["question"]}, timeout=180)
    response_data = response.json()
    diagnosis = response_data.get("diagnosis") or []
    for d in diagnosis:
        results.append({
            "kind": d.get("kind", ""),
            "name": d.get("name", ""),
            "category": d.get("category", ""),
        })
    return response.status_code, results

def identity(d: dict) -> tuple:
    name = re.sub(r"-[a-z0-9]{8,10}$", "", d["name"])
    return (d.get("kind", ""), name)

def compare_results(expected: list[dict], outputs: list[dict]):
    exp = {identity(d): d.get("category", "") for d in expected}
    act = {identity(d): d.get("category", "") for d in outputs}

    correct = [k for k in exp if k in act and exp[k] == act[k]]
    incorrect = [k for k in exp if k in act and exp[k] != act[k]]
    missing = [k for k in exp if k not in act]
    false_positives = [k for k in act if k not in exp]

    return {
        "pass": not incorrect and not missing and not false_positives,
        "correct": correct,
        "incorrect": incorrect,
        "missing": missing,
        "false_positives": false_positives,
    }

if __name__ == "__main__":
    cases = load_cases()
    passed = 0
    for case in cases:
        expected = expected_results(case)
        status_code, outputs = agent_results(case)
        results = compare_results(expected, outputs)
        expected_status = case.get("expect_status", 200)
        results["pass"] = results["pass"] and status_code == expected_status
        status = "PASS" if results["pass"] else "FAIL"
        print(f"{status} {case['id']}")
        if not results["pass"]:
            print(f"            Status: expected {expected_status}, got {status_code}")
            print(f"            Incorrect: {results['incorrect']}")
            print(f"            Missing: {results['missing']}")
            print(f"            FalsePositives: {results['false_positives']}")
            print(f"            Expected: {expected}']")
            print(f"            Outputs: {outputs}']")
        passed += results["pass"]
    rate = passed / len(cases) * 100
    print(f"\n Success rate: {rate}%")
    sys.exit(0 if rate >= THRESHOLD else 1)
