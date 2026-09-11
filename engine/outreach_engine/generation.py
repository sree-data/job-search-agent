"""Generation: thin by design. Builds the prompt from verified inputs, calls
the model, and hands the draft to the quality gate. Provider-agnostic: pass
any `call(prompt) -> str`. The gate loop retries with the gate's reasons
appended, up to `max_attempts`, then escalates to the user instead of
lowering the bar.
"""
from __future__ import annotations
from typing import Callable
from .models import Candidate, Contact, Job, Message, Channel
from .quality_gate import MessageQualityGate, GateResult

STRUCTURE = {
    Channel.LINKEDIN_NOTE: "One sentence under 200 characters: the hook about them, then why you want to connect. No pitch, no ask.",
    Channel.LINKEDIN_MESSAGE: "60-100 words. Sentence 1: something specific about them (use the hook). Sentences 2-3: one proof point of the candidate's that matches their stack or problem. Last sentence: one small, specific ask. Sign off with the candidate's first name only.",
    Channel.EMAIL: "Under 120 words. Subject under 7 words and specific. Same structure as a LinkedIn message. Signature: first name, one-line role, LinkedIn URL.",
}


def build_prompt(c: Candidate, contact: Contact, job: Job, channel: Channel, voice_samples: list[str],
                 hooks: list[str], proof_point: str, mention_sponsorship: bool, feedback: list[str] | None = None) -> str:
    p = [
        "Write a cold message on behalf of a job seeker. Output only the message (and a Subject: line first if email).",
        f"CHANNEL: {channel.value}. FORMAT: {STRUCTURE[channel]}",
        f"RECIPIENT: {contact.name}, {contact.title}, {job.company}. Type: {contact.type.value}.",
        "HOOKS (verified facts about the recipient/company; use exactly one, name it specifically): " + " | ".join(hooks),
        f"SHARED CONNECTION (use it honestly if present): {contact.shared_hook or 'none'}",
        f"ROLE: {job.title} — {job.url}",
        f"PROOF POINT (the only claim you may make about the candidate): {proof_point}",
        "OTHER VERIFIED FACTS you may reference: " + "; ".join(sorted(c.facts)),
        "WORK AUTHORIZATION: " + ("state plainly that the candidate will need visa sponsorship, in one clause, near the end." if mention_sponsorship else "do not mention."),
        "VOICE: match the sentence length, rhythm and word choices of these samples the candidate wrote:\n" + "\n---\n".join(voice_samples),
        "RULES: open with them, not the sender. No exclamation marks. No 'I hope this finds you well', 'reaching out', 'passionate', 'leverage', 'love to', 'excited'. No generic 'any opportunities?'. Plain sentences, contractions fine. If it could be sent unchanged to someone else, it's wrong.",
    ]
    if feedback:
        p.append("PREVIOUS DRAFT FAILED REVIEW FOR: " + "; ".join(feedback) + ". Fix every item.")
    return "\n\n".join(p)


def generate(call: Callable[[str], str], gate: MessageQualityGate, c: Candidate, contact: Contact, job: Job,
             channel: Channel, voice_samples: list[str], hooks: list[str], proof_point: str,
             mention_sponsorship: bool, recent_bodies: list[str], max_attempts: int = 3) -> tuple[Message | None, GateResult]:
    feedback: list[str] = []
    last: GateResult | None = None
    for _ in range(max_attempts):
        raw = call(build_prompt(c, contact, job, channel, voice_samples, hooks, proof_point, mention_sponsorship, feedback))
        subject, body = _split(raw)
        m = Message(contact_id=contact.id, channel=channel, subject=subject, body=body,
                    hook_entities=set(hooks) | ({contact.shared_hook} if contact.shared_hook else set()) | {job.company},
                    claims={proof_point})
        last = gate.check(m, c, recent_bodies)
        if last.passed:
            return m, last
        feedback = last.reasons
    return None, last   # escalate to the user with reasons; never ship a failing draft


def _split(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    if raw.lower().startswith("subject:"):
        first, _, rest = raw.partition("\n")
        return first[8:].strip(), rest.strip()
    return "", raw
