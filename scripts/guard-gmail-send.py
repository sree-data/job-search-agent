#!/usr/bin/env python3
"""PreToolUse guard for mcp__claude_ai_Gmail__send_message.

The daily run may email Alex its own summary, and nothing else. Permission rules match
tool names, not tool arguments, so "only this recipient" cannot be written as an
allow/deny rule. This hook reads the tool input on stdin and denies the call unless
every recipient is exactly the one allowed address.

Fails closed: unparseable input, no recipient field, or any extra recipient => deny.
Outreach to contacts still goes only through /send-email, with Alex present.
"""
import json
import re
import sys

ALLOWED = "alex.rivera@example.com"

RECIP_KEY = re.compile(
    r"^(to|cc|bcc|recipient|recipients|to_recipients|toRecipients|"
    r"cc_recipients|ccRecipients|bcc_recipients|bccRecipients)$",
    re.I,
)
ADDR = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def emit(decision: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def collect(node, key=None, found=None):
    if found is None:
        found = set()
    if isinstance(node, dict):
        for k, v in node.items():
            collect(v, k, found)
    elif isinstance(node, list):
        for v in node:
            collect(v, key, found)
    elif isinstance(node, str) and key and RECIP_KEY.match(key):
        for a in ADDR.findall(node):
            found.add(a.lower())
    return found


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        emit("deny", f"guard-gmail-send could not parse the tool input ({e}). "
                     f"Denying by default.")

    tool = data.get("tool_name", "")
    if tool and tool != "mcp__claude_ai_Gmail__send_message":
        emit("allow", f"Guard does not apply to {tool}.")

    found = collect(data.get("tool_input") or {})
    if not found:
        emit("deny", "No recipient field found in the send_message input. Denying by "
                     f"default; the daily run may only email {ALLOWED}.")

    extra = sorted(found - {ALLOWED})
    if extra:
        emit("deny", f"Blocked: the unattended daily run may only email {ALLOWED}. "
                     f"Refused recipients: {', '.join(extra)}. "
                     "Outreach goes through /send-email with Alex present.")

    emit("allow", f"Self-send to {ALLOWED} only.")


if __name__ == "__main__":
    main()
