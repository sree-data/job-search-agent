"""Job-fit ranking.

Design: a small, interpretable linear model over hand-built features, with
priors that make it useful on day one and a fit() that re-weights from real
outcomes (did this job produce an interview?). This beats a black box for a
product because (a) every score is explainable to the user, (b) it works with
zero data, (c) it gets better per user and per cohort as outcomes arrive.

Text similarity uses TF-IDF cosine between the candidate's target titles /
skills and the posting. Swap `_text_sim` for an embedding model when you have
the budget; the rest of the pipeline doesn't change.
"""
from __future__ import annotations
from datetime import date
import math
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from .models import Candidate, Job, Outcome, Sponsorship

SENIOR_WORDS = {"senior", "sr", "staff", "lead", "principal", "manager", "director", "head", "architect"}
JUNIOR_WORDS = {"junior", "jr", "entry", "associate", "i", "ii", "1", "2", "early"}

# Priors: what a good recruiter would weight before seeing any data.
PRIOR_WEIGHTS = {
    "title_sim": 2.2,
    "skill_overlap": 1.8,
    "location": 1.6,
    "seniority_fit": 1.4,
    "sponsorship": 2.0,      # only applies when candidate needs it
    "industry": 0.6,
    "recency": 0.5,
    "company_sponsor_history": 0.8,
}
PRIOR_BIAS = -4.5


class JobFitRanker:
    def __init__(self, weights: dict[str, float] | None = None, bias: float = PRIOR_BIAS):
        self.weights = dict(weights or PRIOR_WEIGHTS)
        self.bias = bias
        self._model: LogisticRegression | None = None
        self._feature_names = list(PRIOR_WEIGHTS)

    # ---------- features ----------
    def features(self, c: Candidate, j: Job, today: date | None = None) -> dict[str, float]:
        today = today or date.today()
        f: dict[str, float] = {}
        f["title_sim"] = self._text_sim(" ".join(c.target_titles), j.title)
        f["skill_overlap"] = self._skill_overlap(c.skills, j.skills or self._extract_skills(j.description, c.skills))
        f["location"] = self._location(c.target_locations, j.location)
        f["seniority_fit"] = self._seniority(c.years_experience, j)
        f["sponsorship"] = self._sponsorship(c, j)
        f["industry"] = self._industry(c.industries, j.industry)
        age = max(0, (today - j.posted).days)
        f["recency"] = math.exp(-age / 10.0)              # 1.0 today, ~0.5 at a week, ~0.05 at a month
        f["company_sponsor_history"] = float(j.company_sponsor_history) if c.needs_sponsorship else 0.0
        return f

    @staticmethod
    def _text_sim(a: str, b: str) -> float:
        if not a.strip() or not b.strip():
            return 0.0
        v = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit([a, b])
        m = v.transform([a, b])
        return float((m[0] @ m[1].T).toarray()[0, 0])

    @staticmethod
    def _skill_overlap(cand: set[str], job: set[str]) -> float:
        if not job:
            return 0.3   # unknown, mild prior
        return len(cand & job) / len(job)

    @staticmethod
    def _extract_skills(text: str, vocab: set[str]) -> set[str]:
        t = text.lower()
        return {s for s in vocab if s in t}

    @staticmethod
    def _location(targets: list[str], loc: str) -> float:
        loc = loc.lower()
        if any(t in loc for t in targets):
            return 1.0
        if "remote" in loc and "remote" in targets:
            return 1.0
        if "hybrid" in loc and any(t in loc for t in targets):
            return 0.8
        return 0.0

    @staticmethod
    def _seniority(years: float, j: Job) -> float:
        words = j.seniority_words or set(j.title.lower().replace("/", " ").split())
        if words & SENIOR_WORDS and years < 6:
            return -1.0   # actively wrong level; costs the job real points
        if words & JUNIOR_WORDS:
            return 1.0 if years <= 5 else 0.5
        return 0.8   # unmarked title, probably mid

    @staticmethod
    def _sponsorship(c: Candidate, j: Job) -> float:
        if not c.needs_sponsorship:
            return 1.0
        return {Sponsorship.YES: 1.0, Sponsorship.UNKNOWN: 0.5, Sponsorship.NO: -1.0}[j.sponsorship]

    @staticmethod
    def _industry(prefs: list[str], ind: str) -> float:
        if not ind or not prefs:
            return 0.5
        ind = ind.lower()
        for rank, p in enumerate(prefs):
            if p in ind:
                return 1.0 - 0.25 * rank
        return 0.2

    # ---------- scoring ----------
    def score(self, c: Candidate, j: Job, today: date | None = None) -> tuple[float, dict[str, float]]:
        """Returns (probability-like score 0..1, per-feature contributions for explanation)."""
        f = self.features(c, j, today)
        if c.needs_sponsorship and j.sponsorship == Sponsorship.NO:
            return 0.0, {k: 0.0 for k in f} | {"sponsorship": -99.0}   # hard gate
        contrib = {k: self.weights.get(k, 0.0) * v for k, v in f.items()}
        z = self.bias + sum(contrib.values())
        return 1 / (1 + math.exp(-z)), contrib

    def rank(self, c: Candidate, jobs: list[Job], today: date | None = None) -> list[tuple[Job, float, dict[str, float]]]:
        out = [(j, *self.score(c, j, today)) for j in jobs]
        return sorted(out, key=lambda t: t[1], reverse=True)

    def explain(self, contrib: dict[str, float], top: int = 3) -> str:
        pos = sorted((k for k in contrib if contrib[k] > 0), key=lambda k: -contrib[k])[:top]
        neg = sorted((k for k in contrib if contrib[k] <= 0), key=lambda k: contrib[k])[:1]
        s = "for: " + ", ".join(pos) if pos else ""
        if neg and contrib[neg[0]] < 0:
            s += "; against: " + neg[0]
        return s

    # ---------- learning ----------
    def fit(self, outcomes: list[Outcome], min_rows: int = 30, blend: float = 0.5) -> bool:
        """Re-weight from outcomes. Blends learned weights with priors so a
        handful of noisy results can't wreck the ranking. Returns True if fitted."""
        rows = [o for o in outcomes if o.applied]
        if len(rows) < min_rows or len({o.label for o in rows}) < 2:
            return False
        X = np.array([[o.features.get(k, 0.0) for k in self._feature_names] for o in rows])
        y = np.array([o.label for o in rows])
        m = LogisticRegression(C=0.5, max_iter=500).fit(X, y)
        learned = dict(zip(self._feature_names, m.coef_[0]))
        n = len(rows)
        a = min(blend, n / (n + 100))    # more data → trust the fit more, capped at `blend`
        self.weights = {k: (1 - a) * PRIOR_WEIGHTS[k] + a * learned[k] for k in self._feature_names}
        self.bias = (1 - a) * PRIOR_BIAS + a * float(m.intercept_[0])
        self._model = m
        return True
