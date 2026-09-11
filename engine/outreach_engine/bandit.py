"""Message-angle bandit.

Every message is an arm: (hook kind, proof-point id, ask type). Rewards are
replies (and, weighted higher, interviews). Thompson sampling over Beta
posteriors picks the angle to write next, so the product learns per cohort
what actually gets answered instead of guessing. Competitors at best A/B two
templates; most don't measure at all.

Cohort key is up to the caller (e.g. target_role + contact_type). Start the
posteriors from a shared prior so a new cohort borrows from the global one.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import random

ASK_TYPES = ("fifteen_minutes", "one_question", "right_person", "referral_direct")


@dataclass(frozen=True)
class Arm:
    hook_kind: str
    proof_id: str
    ask: str


@dataclass
class Posterior:
    alpha: float = 1.0
    beta: float = 1.0

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


@dataclass
class AngleBandit:
    seed: int = 0
    reply_reward: float = 1.0
    interview_reward: float = 3.0
    cohorts: dict[str, dict[Arm, Posterior]] = field(default_factory=dict)
    global_post: dict[Arm, Posterior] = field(default_factory=dict)

    def __post_init__(self):
        self.rng = random.Random(self.seed)

    def _post(self, cohort: str, arm: Arm) -> Posterior:
        c = self.cohorts.setdefault(cohort, {})
        if arm not in c:
            g = self.global_post.get(arm)
            # new cohort inherits a softened copy of the global belief
            c[arm] = Posterior(1 + (g.alpha - 1) * 0.3, 1 + (g.beta - 1) * 0.3) if g else Posterior()
        return c[arm]

    def choose(self, cohort: str, candidates: list[Arm]) -> Arm:
        """Thompson sampling: draw from each arm's posterior, take the max."""
        return max(candidates, key=lambda a: self._post(cohort, a).sample(self.rng))

    def update(self, cohort: str, arm: Arm, replied: bool, interviewed: bool = False) -> None:
        r = (self.reply_reward if replied else 0.0) + (self.interview_reward if interviewed else 0.0)
        for p in (self._post(cohort, arm), self.global_post.setdefault(arm, Posterior())):
            p.alpha += r
            p.beta += 1.0 if r == 0 else 0.0

    def report(self, cohort: str) -> list[tuple[Arm, float, int]]:
        c = self.cohorts.get(cohort, {})
        return sorted(((a, p.mean, int(p.alpha + p.beta - 2)) for a, p in c.items()), key=lambda t: -t[1])
