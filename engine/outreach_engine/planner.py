"""Daily plan: where the user's limited attention goes.

Auto-apply products optimize applications per day. This optimizes expected
interviews per unit of the user's effort. Each (job, contact) pair gets an
expected value = job fit × P(reply) × P(interview | reply); the planner then
fills the day's budget greedily under the sequence engine's caps and a
per-company limit, and returns a plan with a one-line reason per item so
the user can see (and override) why each message is on the list.

Cross-tenant collision: if many users of the same product write the same
person in the same week, all of them lose. `RecipientLedger` is a global
(all users) frequency cap on recipients. No job-seeker product does this.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from .models import Job, Contact
from .ranking import JobFitRanker
from .contacts import ContactPrioritizer

RECIPIENT_WEEKLY_CAP = 2       # messages from *all* users combined to one recipient per week


@dataclass
class RecipientLedger:
    log: dict[str, list[datetime]] = field(default_factory=dict)

    def available(self, recipient_key: str, now: datetime) -> bool:
        cutoff = now - timedelta(days=7)
        recent = [t for t in self.log.get(recipient_key, []) if t > cutoff]
        return len(recent) < RECIPIENT_WEEKLY_CAP

    def record(self, recipient_key: str, now: datetime) -> None:
        self.log.setdefault(recipient_key, []).append(now)


@dataclass
class PlanItem:
    job: Job
    contact: Contact
    ev: float
    reason: str


class DailyPlanner:
    def __init__(self, ranker: JobFitRanker, prioritizer: ContactPrioritizer, ledger: RecipientLedger | None = None):
        self.ranker = ranker
        self.prioritizer = prioritizer
        self.ledger = ledger or RecipientLedger()

    def plan(self, candidate, jobs: list[Job], contacts_by_job: dict[str, list[Contact]], now: datetime,
             budget: int = 10, per_company: int = 2, today=None) -> list[PlanItem]:
        items: list[PlanItem] = []
        for job, fit, contrib in self.ranker.rank(candidate, jobs, today):
            if fit <= 0:
                continue
            for c in contacts_by_job.get(job.id, []):
                key = self._recipient_key(c)
                if not self.ledger.available(key, now):
                    continue
                cs = self.prioritizer.score(c)
                ev = fit * cs
                why = f"fit {fit:.2f} ({self.ranker.explain(contrib, top=2)}); {c.type.value}" + (f", hook: {c.shared_hook}" if c.shared_hook else "")
                items.append(PlanItem(job, c, ev, why))
        items.sort(key=lambda i: -i.ev)
        out: list[PlanItem] = []
        company_count: dict[str, int] = {}
        for it in items:
            co = it.job.company
            if company_count.get(co, 0) >= per_company:
                continue
            out.append(it)
            company_count[co] = company_count.get(co, 0) + 1
            if len(out) == budget:
                break
        return out

    def commit(self, plan: list[PlanItem], now: datetime) -> None:
        for it in plan:
            self.ledger.record(self._recipient_key(it.contact), now)

    @staticmethod
    def _recipient_key(c: Contact) -> str:
        return f"{c.name.lower().strip()}@{c.title.lower().strip()}"
