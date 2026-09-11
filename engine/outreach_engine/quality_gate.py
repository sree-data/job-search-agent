"""Message quality gate.

This is the component that separates a product people trust from one that
gets them ignored (or banned). Every draft passes through it before a user
sees it. It answers five questions, each with a hard pass/fail and a reason
the user can read:

  1. Is it the right length for the channel?
  2. Does it open with them, not the sender?
  3. Is it specific to this person? (named hooks present, not a template —
     measured as cosine similarity against the sender's recent messages)
  4. Is every claim about the candidate a verified fact?
  5. Is it free of the phrases that mark it as machine-written or mass-sent?

Failed drafts go back to the generator with the reasons, not to the user.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from .models import Message, Channel, Candidate

LIMITS = {   # (min_words, max_words) — chars for the LinkedIn note
    Channel.LINKEDIN_NOTE: (8, 200),      # chars
    Channel.LINKEDIN_MESSAGE: (30, 80),
    Channel.EMAIL: (40, 120),
}
BANNED = [
    "i hope this message finds you well", "i hope this finds you well", "i came across your profile",
    "i'm reaching out", "i am reaching out", "reaching out to", "passionate", "leverage", "synergy",
    "i'd love to", "i would love to", "excited to", "aligns perfectly", "seasoned", "results-driven",
    "delve", "fast-paced", "any opportunities", "pick your brain", "just following up", "bumping this",
    "touch base", "circle back", "i'm confident that", "proven track record", "dynamic", "game-changer",
    "dear sir/madam", "to whom it may concern", "let me know",
]
SENDER_OPENERS = re.compile(r"^\s*(i|i'm|i am|my name|as a|i've|i have)\b", re.I)
GENERIC_ASKS = re.compile(r"(any (open )?(roles|positions|opportunities))|(let me know if)", re.I)
MAX_TEMPLATE_SIM = 0.55    # cosine vs. sender's recent messages; above this it's a template


@dataclass
class GateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    specificity: float = 0.0
    template_similarity: float = 0.0
    words: int = 0


class MessageQualityGate:
    def __init__(self, banned: list[str] | None = None, max_template_sim: float = MAX_TEMPLATE_SIM):
        self.banned = [b.lower() for b in (banned or BANNED)]
        self.max_template_sim = max_template_sim

    def check(self, m: Message, candidate: Candidate, recent_bodies: list[str] | None = None) -> GateResult:
        r = GateResult(passed=True)
        body = m.body.strip()
        text = body.lower()
        words = len(body.split())
        r.words = words

        # 1. length
        lo, hi = LIMITS[m.channel]
        if m.channel == Channel.LINKEDIN_NOTE:
            n = len(body)
            if n > hi or n < lo:
                r.reasons.append(f"length {n} chars, must be {lo}-{hi}")
        elif words < lo or words > hi:
            r.reasons.append(f"length {words} words, must be {lo}-{hi}")
        if m.channel == Channel.EMAIL:
            if not m.subject.strip():
                r.reasons.append("missing subject")
            elif len(m.subject.split()) > 7:
                r.reasons.append("subject over 7 words")

        # 2. opens with them
        first = re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0]
        if SENDER_OPENERS.match(first):
            r.reasons.append("first sentence is about the sender, not the reader")

        # 3. specificity
        hooks = {h.lower() for h in m.hook_entities if h}
        present = [h for h in hooks if h in text]
        r.specificity = len(present)
        if len(present) == 0:
            r.reasons.append("no specific hook about the reader appears in the text")
        if recent_bodies:
            r.template_similarity = self._max_sim(body, recent_bodies)
            if r.template_similarity > self.max_template_sim:
                r.reasons.append(f"reads like a template (similarity {r.template_similarity:.2f} to a recent message)")

        # 4. claims
        unverified = {c for c in m.claims if c.lower() not in {f.lower() for f in candidate.facts}}
        if unverified:
            r.reasons.append("unverified claims about candidate: " + ", ".join(sorted(unverified)))

        # 5. banned phrases and generic asks
        hits = [b for b in self.banned if b in text]
        if hits:
            r.reasons.append("banned phrases: " + ", ".join(hits))
        if GENERIC_ASKS.search(body):
            r.reasons.append("ask is generic; ask one specific question or for 15 minutes")
        if "!" in body:
            r.reasons.append("exclamation marks")
        if body.count("\n\n") > 3:
            r.reasons.append("too many paragraphs for a cold message")

        r.passed = not r.reasons
        return r

    @staticmethod
    def _max_sim(body: str, others: list[str]) -> float:
        docs = [body] + others
        v = TfidfVectorizer(ngram_range=(1, 3), stop_words="english").fit(docs)
        m = v.transform(docs)
        sims = (m[0] @ m[1:].T).toarray()[0]
        return float(sims.max()) if len(sims) else 0.0
