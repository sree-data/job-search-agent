from outreach_engine import Candidate, MessageQualityGate
from outreach_engine.models import Message, Channel

C = Candidate(id="u", skills=set(), years_experience=4, target_titles=[], target_locations=[], needs_sponsorship=True,
              facts={"migrated business objects reporting to power bi for a health system"})

GOOD = ("Your talk at Snowflake Summit on moving Banner's claims pipelines off SSIS covered exactly the problem I spent "
        "last year on: I migrated Business Objects reporting to Power BI for a health system and rebuilt the semantic "
        "model underneath it. I'm looking at the Data Engineer II req on your team. Would 15 minutes next week be "
        "reasonable to ask how the platform team is set up? Alex")

def test_good_message_passes():
    m = Message("c1", Channel.LINKEDIN_MESSAGE, "", GOOD, hook_entities={"Snowflake Summit", "Banner"},
                claims={"migrated business objects reporting to power bi for a health system"})
    r = MessageQualityGate().check(m, C)
    assert r.passed, r.reasons

def test_template_and_banned_phrases_fail():
    body = ("I hope this message finds you well! I'm reaching out because I'm passionate about data and would love to "
            "leverage my skills at your company. Are there any opportunities on your team? Thanks so much!")
    m = Message("c1", Channel.LINKEDIN_MESSAGE, "", body, hook_entities={"Banner"}, claims=set())
    r = MessageQualityGate().check(m, C)
    assert not r.passed
    joined = " ".join(r.reasons)
    assert "banned" in joined and "sender" in joined and "hook" in joined and "generic" in joined and "exclamation" in joined

def test_unverified_claim_fails():
    m = Message("c1", Channel.LINKEDIN_MESSAGE, "", GOOD, hook_entities={"Banner"}, claims={"led a team of ten"})
    r = MessageQualityGate().check(m, C)
    assert any("unverified" in x for x in r.reasons)

def test_near_duplicate_of_recent_send_fails():
    m = Message("c1", Channel.LINKEDIN_MESSAGE, "", GOOD, hook_entities={"Banner"},
                claims={"migrated business objects reporting to power bi for a health system"})
    recent = [GOOD.replace("Banner", "Mayo").replace("Snowflake Summit", "Databricks Summit")]
    r = MessageQualityGate().check(m, C, recent_bodies=recent)
    assert any("template" in x for x in r.reasons)

def test_email_needs_short_specific_subject():
    m = Message("c1", Channel.EMAIL, "A quick question about a few things regarding opportunities", GOOD,
                hook_entities={"Banner"}, claims={"migrated business objects reporting to power bi for a health system"})
    r = MessageQualityGate().check(m, C)
    assert any("subject" in x for x in r.reasons)
