from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
from outreach_engine import SequenceEngine
from outreach_engine.sequence import Thread, State
from outreach_engine.models import Channel

TZ = ZoneInfo("America/Phoenix")

def thread(i="t1", co="Acme", ch=Channel.EMAIL):
    return Thread(id=i, user_id="u", contact_id=f"c{i}", company=co, channel=ch)

def test_lifecycle_and_followup_timing():
    e = SequenceEngine(); t = thread()
    now = datetime(2026, 9, 15, 9, 0, tzinfo=TZ)   # Tuesday
    e.approve(t); e.mark_sent(t, now)
    assert t.state == State.SENT and t.touch == 1
    ok, why = e.can_send(t, now + timedelta(days=2))
    assert not ok and "due" in why
    assert e.due_followups([t], now + timedelta(days=5)) == [t]
    e.mark_sent(t, now + timedelta(days=5)); e.mark_sent(t, now + timedelta(days=12))
    assert not e.can_send(t, now + timedelta(days=20))[0]
    e.close_if_exhausted(t, now + timedelta(days=20)); assert t.state == State.NO_REPLY

def test_reply_halts_sequence():
    e = SequenceEngine(); t = thread(); now = datetime(2026, 9, 15, 9, 0, tzinfo=TZ)
    e.approve(t); e.mark_sent(t, now); e.mark_replied(t, now + timedelta(days=1), "wants to talk")
    assert t.state == State.REPLIED and e.due_followups([t], now + timedelta(days=9)) == []

def test_daily_and_company_caps():
    e = SequenceEngine(); now = datetime(2026, 9, 15, 9, 0, tzinfo=TZ)
    for i in range(3):
        t = thread(f"a{i}", co="Acme"); e.approve(t); e.mark_sent(t, now)
    t4 = thread("a4", co="Acme"); e.approve(t4)
    assert "Acme" in e.can_send(t4, now)[1]
    for i in range(7):
        t = thread(f"b{i}", co=f"Co{i}"); e.approve(t); e.mark_sent(t, now)
    t = thread("z", co="Zed"); e.approve(t)
    assert "daily cap" in e.can_send(t, now)[1]

def test_suppression_is_permanent():
    e = SequenceEngine(); t = thread(); e.approve(t); e.mark_bounced_or_opted_out(t)
    assert not e.can_send(t, datetime(2026, 9, 15, 9, 0, tzinfo=TZ))[0]

def test_send_slot_skips_weekend_and_lands_in_window():
    e = SequenceEngine(); t = thread()
    sat = datetime(2026, 9, 12, 14, 0, tzinfo=TZ)   # Saturday afternoon
    slot = e.next_send_slot(t, sat)
    assert slot.weekday() == 1 and slot.hour == 8    # Tuesday 8am (Monday skipped on purpose)
    fri = datetime(2026, 9, 11, 7, 0, tzinfo=TZ)
    assert e.next_send_slot(t, fri).weekday() == 1

def test_cannot_send_unapproved():
    e = SequenceEngine(); t = thread()
    with pytest.raises(ValueError):
        e.mark_sent(t, datetime(2026, 9, 15, 9, 0, tzinfo=TZ))
