from datetime import date, datetime
from zoneinfo import ZoneInfo
from outreach_engine import *
from outreach_engine.models import Sponsorship, ContactType
from outreach_engine.hooks import Hook
from outreach_engine.bandit import Arm
from outreach_engine.replies import ReplyKind

TODAY = date(2026, 9, 10)

def test_hooks_prefer_rare_recent_sourced_authored():
    m = HookMiner()
    for _ in range(40):
        m.observe("We are a leading healthcare provider committed to excellence and innovation in patient care.")
    m.observe("Talk at Snowflake Summit: migrating Lakeside Health System claims pipelines from SSIS to Snowflake streams and tasks.")
    hooks = [
        Hook("Banner is a leading healthcare provider committed to excellence in patient care", "company_page", "https://x/about", None),
        Hook("Migrating claims pipelines from SSIS to Snowflake streams and tasks", "talk", "https://x/talk", date(2026, 6, 1), author_is_contact=True),
        Hook("Banner is hiring a Data Engineer II", "job_posting", "https://x/job", date(2026, 9, 1)),
        Hook("A great hook with no source", "talk", "", date(2026, 9, 1)),
    ]
    top = m.rank(hooks, today=TODAY, k=3)
    assert top[0].kind == "talk" and "SSIS" in top[0].text
    assert all(h.url for h in top)
    assert top[-1].kind == "company_page" or len(top) < 3

def test_hooks_diversify():
    m = HookMiner()
    a = Hook("Migrating claims pipelines from SSIS to Snowflake", "talk", "u1", TODAY)
    b = Hook("Their SSIS to Snowflake claims pipeline migration", "blog", "u2", TODAY)
    c = Hook("Open-sourced a dbt package for HL7 parsing", "repo", "u3", TODAY)
    top = m.rank([a, b, c], today=TODAY, k=2)
    assert {h.url for h in top} == {"u1", "u3"}

def test_bandit_learns_the_better_angle():
    b = AngleBandit(seed=3)
    good = Arm("talk", "p1", "one_question"); bad = Arm("profile_field", "p1", "referral_direct")
    for _ in range(60):
        b.update("de/hiring_manager", good, replied=True)
        b.update("de/hiring_manager", bad, replied=False)
    picks = [b.choose("de/hiring_manager", [good, bad]) for _ in range(50)]
    assert picks.count(good) > 45
    # a new cohort inherits the global belief
    assert b.choose("de/recruiter", [good, bad]) == good

def test_planner_maximizes_ev_and_respects_ledger():
    me = Candidate(id="u", skills={"sql", "snowflake", "python"}, years_experience=4, target_titles=["data engineer"],
                   target_locations=["phoenix", "remote"], needs_sponsorship=True, industries=["health"])
    j1 = Job("j1", "Banner", "Data Engineer II", "sql snowflake python", "Phoenix, AZ", TODAY, industry="healthcare", sponsorship=Sponsorship.YES)
    j2 = Job("j2", "Zed", "Data Engineer", "sql", "Remote", TODAY, industry="fintech", sponsorship=Sponsorship.UNKNOWN)
    cs = {"j1": [Contact("c1", "j1", "A Patel", "Data Platform Manager", ContactType.HIRING_MANAGER, has_public_activity=True, role_relevance=0.9),
                 Contact("c2", "j1", "R Gomez", "Recruiter", ContactType.RECRUITER, role_relevance=0.5),
                 Contact("c3", "j1", "K Reddy", "Data Engineer", ContactType.ENGINEER, role_relevance=0.4)],
          "j2": [Contact("c4", "j2", "B Lee", "Eng Manager", ContactType.HIRING_MANAGER, role_relevance=0.8)]}
    now = datetime(2026, 9, 15, 9, 0, tzinfo=ZoneInfo("America/Phoenix"))
    p = DailyPlanner(JobFitRanker(), ContactPrioritizer())
    plan = p.plan(me, [j1, j2], cs, now, budget=10, per_company=2, today=TODAY)
    assert plan[0].contact.id == "c1" and len([i for i in plan if i.job.company == "Banner"]) == 2
    assert all(i.reason for i in plan)
    # other users of the product already hit A Patel twice this week
    p.ledger.record("a patel@data platform manager", now); p.ledger.record("a patel@data platform manager", now)
    plan2 = p.plan(me, [j1, j2], cs, now, budget=10, per_company=2, today=TODAY)
    assert all(i.contact.id != "c1" for i in plan2)

def test_reply_classifier():
    k, _ = classify_reply("Thanks Alex, happy to chat. Are you free Thursday afternoon?")
    assert k == ReplyKind.INTERESTED
    k, _ = classify_reply("I'm not the right person for this, reach out to Priya Nair who runs the platform team.")
    assert k == ReplyKind.REDIRECT
    k, _ = classify_reply("Unfortunately we don't sponsor visas for this role.")
    assert k == ReplyKind.REJECTION
    k, _ = classify_reply("I am out of the office until Sept 22 with limited access to email.")
    assert k == ReplyKind.AUTO_REPLY
    k, _ = classify_reply("Delivery has failed to these recipients: user unknown")
    assert k == ReplyKind.BOUNCE
    k, _ = classify_reply("ok\n> On Tue, Alex wrote: happy to chat?")
    assert k == ReplyKind.UNCLEAR
    assert "suppress" in next_action(ReplyKind.BOUNCE)
