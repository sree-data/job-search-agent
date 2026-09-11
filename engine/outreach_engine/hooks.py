"""Hook mining with provenance.

Competitors "personalize" by merging profile fields (name, title, company)
into a template. Recipients see through that instantly. A hook that gets a
reply is a *rare, recent, sourced* fact about the reader's own work: a talk
they gave, a migration they wrote about, a repo they maintain.

This module turns raw research text into ranked hooks, each carrying the URL
it came from. Ranking = type prior × specificity × freshness, where
specificity is how rare the hook's language is across everything we've
collected (a sentence that appears on fifty company pages is boilerplate).
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import math
import re
from collections import Counter

TYPE_PRIOR = {          # how strongly each kind of hook signals "I actually read your work"
    "talk": 1.0, "blog": 0.95, "repo": 0.9, "post": 0.8, "interview": 0.8,
    "job_posting": 0.55, "news": 0.5, "company_page": 0.25, "profile_field": 0.1,
}
_WORD = re.compile(r"[a-z][a-z0-9+#.-]{2,}")
_STOP = set("the and for with that this from are was were have has been into over about their they them our your you will can more than also which when what who how".split())


@dataclass
class Hook:
    text: str            # one sentence, the thing you'd reference
    kind: str            # key of TYPE_PRIOR
    url: str             # provenance; a hook without a source is not a hook
    when: date | None    # publication date if known
    author_is_contact: bool = False   # the reader wrote/said it themselves
    score: float = 0.0

    def cite(self) -> str:
        return f"{self.text} [{self.kind}, {self.url}]"


class HookMiner:
    def __init__(self, half_life_days: float = 240.0):
        self.df: Counter[str] = Counter()   # document frequency of terms across everything mined
        self.n_docs = 0
        self.half_life = half_life_days

    def observe(self, text: str) -> None:
        """Feed every research document through here so specificity has a baseline."""
        self.n_docs += 1
        self.df.update(set(self._terms(text)))

    def _terms(self, text: str) -> list[str]:
        return [w for w in _WORD.findall(text.lower()) if w not in _STOP]

    def specificity(self, text: str) -> float:
        """Mean IDF of the hook's terms, squashed to 0..1. Rare language → high."""
        terms = self._terms(text)
        if not terms or self.n_docs == 0:
            return 0.5
        idf = [math.log((self.n_docs + 1) / (self.df.get(t, 0) + 1)) + 1 for t in terms]
        m = sum(idf) / len(idf)
        return 1 - math.exp(-m / 3)

    def freshness(self, when: date | None, today: date) -> float:
        if when is None:
            return 0.6
        return 0.5 ** (max(0, (today - when).days) / self.half_life)

    def score(self, h: Hook, today: date | None = None) -> float:
        today = today or date.today()
        s = TYPE_PRIOR.get(h.kind, 0.3) * (0.4 + 0.6 * self.specificity(h.text)) * (0.5 + 0.5 * self.freshness(h.when, today))
        if h.author_is_contact:
            s *= 1.5
        if not h.url:
            s = 0.0
        h.score = s
        return s

    def rank(self, hooks: list[Hook], today: date | None = None, k: int = 3) -> list[Hook]:
        for h in hooks:
            self.score(h, today)
        ranked = sorted((h for h in hooks if h.score > 0), key=lambda h: -h.score)
        # diversify: don't hand the generator three hooks about the same thing
        out: list[Hook] = []
        for h in ranked:
            if all(self._overlap(h.text, o.text) < 0.5 for o in out):
                out.append(h)
            if len(out) == k:
                break
        return out

    def _overlap(self, a: str, b: str) -> float:
        ta, tb = set(self._terms(a)), set(self._terms(b))
        return len(ta & tb) / max(1, min(len(ta), len(tb)))
