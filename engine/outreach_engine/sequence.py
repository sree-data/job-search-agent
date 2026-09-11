"""Sequence engine: when to send, when to follow up, when to stop.

State machine per thread:
    draft -> approved -> sent(touch 1) -> [reply?] -> sent(touch 2, +5d) -> [reply?] -> sent(touch 3, +12d) -> closed
Any reply moves the thread to `replied` and halts the sequence. Any bounce or
opt-out puts the address on the suppression list for the whole product.

Hard product rules enforced here, not in prompts:
  - LinkedIn is never sent by the system. LinkedIn steps produce a "paste this"
    task for the user and wait for the user to mark it sent.
  - Per-user daily caps. Per-domain caps (never more than N people at one
    company in a week, which is what gets a sender flagged internally).
  - Send-time windows in the recipient's time zone.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time
from enum import Enum
from zoneinfo import ZoneInfo
from .models import Channel

FOLLOWUP_DAYS = {2: 5, 3: 12}       # touch -> days after touch 1
MAX_TOUCH = 3
DAILY_CAP = {Channel.EMAIL: 10, Channel.LINKEDIN_NOTE: 10, Channel.LINKEDIN_MESSAGE: 10}
COMPANY_WEEKLY_CAP = 3
SEND_DAYS = {1, 2, 3}                 # Tue, Wed, Thu (Mon=0)
SEND_WINDOW = (time(8, 0), time(10, 30))


class State(str, Enum):
    DRAFT = "draft"; APPROVED = "approved"; SENT = "sent"; REPLIED = "replied"
    NO_REPLY = "no_reply"; CLOSED = "closed"; SUPPRESSED = "suppressed"


@dataclass
class Thread:
    id: str
    user_id: str
    contact_id: str
    company: str
    channel: Channel
    recipient_tz: str = "America/Phoenix"
    state: State = State.DRAFT
    touch: int = 0
    first_sent: datetime | None = None
    last_sent: datetime | None = None
    history: list[str] = field(default_factory=list)


class SequenceEngine:
    def __init__(self):
        self.suppression: set[str] = set()            # emails / contact ids that must never be contacted again
        self._sent_log: list[tuple[str, str, Channel, datetime]] = []   # user, company, channel, when

    # ---------- transitions ----------
    def approve(self, t: Thread) -> None:
        if t.state != State.DRAFT:
            raise ValueError(f"can only approve a draft, thread is {t.state}")
        t.state = State.APPROVED

    def can_send(self, t: Thread, now: datetime) -> tuple[bool, str]:
        if t.contact_id in self.suppression:
            return False, "contact is on the suppression list"
        if t.state not in (State.APPROVED, State.SENT):
            return False, f"state is {t.state}"
        if t.touch >= MAX_TOUCH:
            return False, "max touches reached"
        if t.touch > 0 and now < self.next_touch_due(t):
            return False, f"next touch due {self.next_touch_due(t):%Y-%m-%d}"
        used = sum(1 for u, _, ch, when in self._sent_log if u == t.user_id and ch == t.channel and when.date() == now.date())
        if used >= DAILY_CAP[t.channel]:
            return False, f"daily cap for {t.channel.value} reached"
        week_ago = now - timedelta(days=7)
        same_co = sum(1 for u, co, _, when in self._sent_log if u == t.user_id and co == t.company and when > week_ago)
        if t.touch == 0 and same_co >= COMPANY_WEEKLY_CAP:
            return False, f"already contacted {COMPANY_WEEKLY_CAP} people at {t.company} this week"
        return True, "ok"

    def mark_sent(self, t: Thread, now: datetime) -> None:
        """The system calls this after an email goes out; the user calls it after pasting a LinkedIn message."""
        ok, why = self.can_send(t, now)
        if not ok:
            raise ValueError(why)
        t.touch += 1
        t.first_sent = t.first_sent or now
        t.last_sent = now
        t.state = State.SENT
        t.history.append(f"touch {t.touch} sent {now:%Y-%m-%d %H:%M}")
        self._sent_log.append((t.user_id, t.company, t.channel, now))

    def mark_replied(self, t: Thread, now: datetime, gist: str = "") -> None:
        t.state = State.REPLIED
        t.history.append(f"replied {now:%Y-%m-%d}: {gist}")

    def mark_bounced_or_opted_out(self, t: Thread) -> None:
        t.state = State.SUPPRESSED
        self.suppression.add(t.contact_id)

    def close_if_exhausted(self, t: Thread, now: datetime) -> None:
        if t.state == State.SENT and t.touch >= MAX_TOUCH and t.first_sent and now > t.first_sent + timedelta(days=FOLLOWUP_DAYS[MAX_TOUCH] + 7):
            t.state = State.NO_REPLY

    # ---------- timing ----------
    def next_touch_due(self, t: Thread) -> datetime:
        assert t.first_sent
        return t.first_sent + timedelta(days=FOLLOWUP_DAYS[t.touch + 1])

    def next_send_slot(self, t: Thread, earliest: datetime) -> datetime:
        """First Tue–Thu 8:00–10:30 in the recipient's time zone at or after `earliest`."""
        tz = ZoneInfo(t.recipient_tz)
        cur = earliest.astimezone(tz)
        for _ in range(14):
            start = datetime.combine(cur.date(), SEND_WINDOW[0], tz)
            end = datetime.combine(cur.date(), SEND_WINDOW[1], tz)
            if cur.weekday() in SEND_DAYS and cur <= end:
                return max(cur, start)
            cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tz)
        raise RuntimeError("no send slot found")

    def due_followups(self, threads: list[Thread], now: datetime) -> list[Thread]:
        out = []
        for t in threads:
            if t.state == State.SENT and t.touch < MAX_TOUCH and now >= self.next_touch_due(t):
                out.append(t)
        return out
