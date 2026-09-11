"""Reply classification → next action.

A reply is not one thing. The sequence must stop for all of them, but what
the user should do next differs. Rules handle the unambiguous cases with
no model call (auto-replies, out-of-office, bounces, flat rejections); the
ambiguous remainder is routed to an LLM through `llm_classify` if provided.
"""
from __future__ import annotations
from enum import Enum
import re
from typing import Callable


class ReplyKind(str, Enum):
    INTERESTED = "interested"          # wants to talk / asks for resume / proposes time
    REDIRECT = "redirect"              # "talk to X instead" — a new contact, warm
    NOT_NOW = "not_now"                # no headcount, try later
    REJECTION = "rejection"            # no, and not later
    AUTO_REPLY = "auto_reply"          # OOO / auto-response, thread is still live
    BOUNCE = "bounce"                  # address dead → suppression
    UNCLEAR = "unclear"


NEXT_ACTION = {
    ReplyKind.INTERESTED: "reply within 4 hours; propose two times; attach resume only if asked",
    ReplyKind.REDIRECT: "thank them; add the named person as a referral contact with this thread as the hook",
    ReplyKind.NOT_NOW: "thank them; set a 60-day check-in; no further touches",
    ReplyKind.REJECTION: "one-line thanks; close thread",
    ReplyKind.AUTO_REPLY: "no action; keep follow-up schedule, shift by the return date if one is given",
    ReplyKind.BOUNCE: "suppress address; find another channel for this contact",
    ReplyKind.UNCLEAR: "show to user",
}

_RULES: list[tuple[ReplyKind, re.Pattern]] = [
    (ReplyKind.BOUNCE, re.compile(r"(undeliverable|delivery (has )?failed|address not found|mailbox (is )?full|user unknown|550 )", re.I)),
    (ReplyKind.AUTO_REPLY, re.compile(r"(out of (the )?office|on leave|automatic reply|auto-?reply|away from my desk|limited access to email)", re.I)),
    (ReplyKind.REDIRECT, re.compile(r"(reach out to|talk to|contact|cc'?ing|looping in|the right person is|forward(ed|ing) (this|your))\s+[A-Z][a-z]+", re.I)),
    (ReplyKind.INTERESTED, re.compile(r"(happy to chat|let'?s (talk|chat|set up)|send (me )?(your|a) resume|are you (free|available)|what (time|days) work|calendly|book a time|schedule)", re.I)),
    (ReplyKind.NOT_NOW, re.compile(r"(no (open )?(roles|headcount|positions) (right now|at the moment|currently)|hiring freeze|check back|later this year|not hiring (right now|currently))", re.I)),
    (ReplyKind.REJECTION, re.compile(r"(not a fit|won'?t be moving forward|decided not to|not looking to|unable to sponsor|don'?t sponsor|no sponsorship)", re.I)),
]


def classify(text: str, llm_classify: Callable[[str], str] | None = None) -> tuple[ReplyKind, str]:
    body = _strip_quoted(text)
    for kind, pat in _RULES:
        m = pat.search(body)
        if m:
            return kind, m.group(0)
    if llm_classify:
        label = llm_classify(body).strip().lower()
        try:
            return ReplyKind(label), "llm"
        except ValueError:
            pass
    return ReplyKind.UNCLEAR, ""


def next_action(kind: ReplyKind) -> str:
    return NEXT_ACTION[kind]


def _strip_quoted(text: str) -> str:
    """Drop quoted history so the classifier reads only what they wrote."""
    lines = []
    for ln in text.splitlines():
        if ln.startswith(">") or re.match(r"^(On .+ wrote:|From: |-----Original Message-----)", ln):
            break
        lines.append(ln)
    return "\n".join(lines)
