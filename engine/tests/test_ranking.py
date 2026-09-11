from datetime import date
import random
from outreach_engine import Candidate, Job, JobFitRanker, Outcome
from outreach_engine.models import Sponsorship

def cand():
    return Candidate(id="u1", skills={"sql", "python", "snowflake", "power bi", "azure"}, years_experience=4,
                     target_titles=["data engineer", "analytics engineer"], target_locations=["phoenix", "tempe", "remote"],
                     needs_sponsorship=True, industries=["health", "tech"])

def job(**kw):
    base = dict(id="j", company="Acme Health", title="Data Engineer II", description="sql python snowflake azure pipelines",
                location="Tempe, AZ", posted=date(2026, 9, 8), industry="healthcare", sponsorship=Sponsorship.YES)
    base.update(kw)
    return Job(**base)

def test_good_job_outscores_senior_far_away():
    r = JobFitRanker()
    good = job()
    bad = job(id="b", title="Senior Staff Data Architect", location="Boston, MA", industry="finance", sponsorship=Sponsorship.UNKNOWN)
    (j1, s1, _), (j2, s2, _) = r.rank(cand(), [good, bad], today=date(2026, 9, 10))
    assert j1.id == "j" and s1 > 0.6 and s2 < 0.2

def test_no_sponsorship_is_hard_gate():
    r = JobFitRanker()
    s, contrib = r.score(cand(), job(sponsorship=Sponsorship.NO), today=date(2026, 9, 10))
    assert s == 0.0 and contrib["sponsorship"] == -99.0

def test_explanation_names_top_features():
    r = JobFitRanker()
    _, contrib = r.score(cand(), job(), today=date(2026, 9, 10))
    exp = r.explain(contrib)
    assert exp.startswith("for:") and "skill_overlap" in exp

def test_fit_shifts_weights_toward_signal():
    random.seed(1)
    r = JobFitRanker()
    outs = []
    for i in range(80):   # synthetic world where only skill_overlap predicts interviews
        f = {k: random.random() for k in r.weights}
        outs.append(Outcome(job_id=str(i), features=f, applied=True, interview=f["skill_overlap"] > 0.6))
    assert r.fit(outs)
    assert r.weights["skill_overlap"] > r.weights["industry"]

def test_fit_refuses_with_too_little_data():
    r = JobFitRanker()
    assert not r.fit([Outcome(job_id="1", features={}, applied=True, interview=True)] * 5)
