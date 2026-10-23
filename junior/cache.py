import redis
import logging
import hashlib
import json
import time
import os

LONG_TTL = 7 * 24 * 3600
SHORT_TTL = 4 * 3600

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
redis_client = None

def init():
    global redis_client
    redis_client = None
    client = redis.Redis(
        host=REDIS_HOST,
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        client.ping()
    except redis.RedisError as e:
        logging.warning(f"Redis not reachable; cache disabled: {e}")
        return
    redis_client = client
    logging.info("Redis client reachable")

def make_key(entry: dict, prompt_version: str) -> str:
    reason = entry.get("reason") or "unknown"
    # Event messages embed generated names and counts, so they'd never repeat.
    stable_message = reason not in ["CrashLoopBackOff"] and entry["category"] != "event"
    message = (entry.get("message") or "") if stable_message else ""
    msg_hash = hashlib.sha1(
        (message).encode()).hexdigest()[:8]
    owner = entry.get("owner") or entry["name"]
    container = entry.get("container") or "-"
    key = ":".join(["junior", prompt_version, entry["namespace"], entry["kind"], owner, container, entry["category"], reason, msg_hash])
    return key

def get_entry(key: str):
    if redis_client is None:
        return None
    try:
        raw = redis_client.get(key)
        return json.loads(raw) if raw else None
    except redis.RedisError as e:
        logging.warning(f"Cache fetch failed for {key} {e}")
        return None

def set_entry(key, diagnosis: dict):
    if redis_client is None:
        return
    ttl = LONG_TTL if diagnosis.get("category") == "k8s_issue" else SHORT_TTL
    value = {
        "category": diagnosis.get("category"),
        "summary": diagnosis.get("summary"),
        "created_at": int(time.time()),
    }
    try:
        redis_client.set(key, json.dumps(value), ex=ttl)
    except redis.RedisError as e:
        logging.warning(f"Cache set failed for {key} {e}")

def main():
    init()
    logging.info("Redis client initialized")

if __name__ == "__main__":
    main()