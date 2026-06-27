"""
Live formatter for agent stream-json output (works for Amp --stream-json and
Claude --output-format stream-json, which share the schema).

Reads JSON-lines from stdin and prints a readable, real-time view of what the
agent is doing: text, tool calls, tool results, and the final result.

Usage (the scripts wire this up for you with -Stream):
    amp    -x "<prompt>" --stream-json                       | python -u stream_fmt.py
    claude -p "<prompt>" --output-format stream-json --verbose | python -u stream_fmt.py
"""
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def brief(obj, n=120):
    s = json.dumps(obj, ensure_ascii=False) if not isinstance(obj, str) else obj
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


for raw in sys.stdin:
    raw = raw.strip()
    if not raw:
        continue
    try:
        ev = json.loads(raw)
    except json.JSONDecodeError:
        print(raw, flush=True)
        continue

    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init":
        sid = ev.get("session_id", "?")
        print(f"\033[36m* session {sid}\033[0m", flush=True)
        if str(sid).startswith("T-"):
            print(f"  watch: https://ampcode.com/threads/{sid}", flush=True)
    elif t == "assistant":
        for block in ev.get("message", {}).get("content", []):
            bt = block.get("type")
            if bt == "text" and block.get("text", "").strip():
                print(f"\033[37m{block['text'].strip()}\033[0m", flush=True)
            elif bt == "thinking" and block.get("thinking", "").strip():
                print(f"\033[90m  ...thinking: {brief(block['thinking'])}\033[0m", flush=True)
            elif bt == "tool_use":
                print(f"\033[33m  -> {block.get('name','tool')}: {brief(block.get('input',{}))}\033[0m", flush=True)
    elif t == "user":
        for block in ev.get("message", {}).get("content", []):
            if block.get("type") == "tool_result":
                content = block.get("content", "")
                if isinstance(content, list):
                    content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                print(f"\033[32m  [ok] {brief(content)}\033[0m", flush=True)
    elif t == "result":
        ms = ev.get("duration_ms", "?")
        err = ev.get("is_error")
        mark = "\033[31m== error" if err else "\033[36m== done"
        print(f"{mark} in {ms} ms\033[0m", flush=True)
