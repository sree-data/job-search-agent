"""Who to write to first.

Reply-rate priors by contact type come from what cold-outreach practitioners
consistently report: a real shared hook beats everything, the person who owns
the headcount beats the person who screens for it, and a recruiter with no
open req rarely replies. These are starting points; replace with your own
measured rates per type once you have them (`update_priors`).
"""
from __future__ import annotations
from .models import Contact, ContactType

REPLY_PRIOR = {
    ContactType.REFERRAL: 0.60,
    ContactType.ALUMNI: 0.35,
    ContactType.HIRING_MANAGER: 0.18,
    ContactType.ENGINEER: 0.14,
    ContactType.RECRUITER: 0.10,
}
# Recruiters convert replies to interviews at a higher rate than engineers do,
# which partly offsets their low reply rate.
INTERVIEW_GIVEN_REPLY = {
    ContactType.REFERRAL: 0.55,
    ContactType.ALUMNI: 0.35,
    ContactType.HIRING_MANAGER: 0.50,
    ContactType.ENGINEER: 0.25,
    ContactType.RECRUITER: 0.45,
}


class ContactPrioritizer:
    def __init__(self):
        self.reply_prior = dict(REPLY_PRIOR)
        self.interview_prior = dict(INTERVIEW_GIVEN_REPLY)
        self._counts: dict[ContactType, list[int]] = {t: [0, 0, 0] for t in ContactType}  # sent, replied, interviewed

    def score(self, c: Contact) -> float:
        """Expected value of one message = P(reply) * P(interview | reply), with
        multipliers for the things that actually move reply rate."""
        p_reply = self.reply_prior[c.type]
        if c.shared_hook:
            p_reply *= 1.6
        if c.has_public_activity:
            p_reply *= 1.3          # something concrete to anchor on
        if c.has_email:
            p_reply *= 1.15         # email + LinkedIn beats LinkedIn alone
        p_reply = min(p_reply, 0.9)
        p_int = self.interview_prior[c.type] * (0.5 + 0.5 * c.role_relevance)
        return p_reply * p_int

    def rank(self, contacts: list[Contact]) -> list[tuple[Contact, float]]:
        return sorted(((c, self.score(c)) for c in contacts), key=lambda t: t[1], reverse=True)

    def pick(self, contacts: list[Contact], k: int = 1) -> list[Contact]:
        """Top-k, but never two of the same type for the same job in one pass —
        writing to two recruiters at once looks like spam."""
        seen: set[ContactType] = set()
        out = []
        for c, _ in self.rank(contacts):
            if c.type in seen:
                continue
            seen.add(c.type)
            out.append(c)
            if len(out) == k:
                break
        return out

    # ---------- learning ----------
    def record(self, c: Contact, replied: bool, interviewed: bool = False) -> None:
        s = self._counts[c.type]
        s[0] += 1; s[1] += int(replied); s[2] += int(interviewed)

    def update_priors(self, min_sent: int = 25) -> None:
        """Bayesian-ish: shrink observed rates toward the prior until there's enough data."""
        for t, (sent, rep, intv) in self._counts.items():
            if sent < min_sent:
                continue
            w = sent / (sent + 50)
            self.reply_prior[t] = (1 - w) * REPLY_PRIOR[t] + w * rep / sent
            if rep:
                self.interview_prior[t] = (1 - w) * INTERVIEW_GIVEN_REPLY[t] + w * intv / rep
