from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional


class ContactType(str, Enum):
    ALUMNI = "alumni"          # shared school / employer / origin, real hook
    REFERRAL = "referral"      # someone who already offered to refer
    HIRING_MANAGER = "hiring_manager"
    ENGINEER = "engineer"      # IC on the target team
    RECRUITER = "recruiter"


class Channel(str, Enum):
    LINKEDIN_NOTE = "linkedin_note"
    LINKEDIN_MESSAGE = "linkedin_message"
    EMAIL = "email"


class Sponsorship(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


@dataclass
class Candidate:
    id: str
    skills: set[str]                    # normalized, lowercase
    years_experience: float
    target_titles: list[str]
    target_locations: list[str]         # e.g. ["phoenix", "tempe", "remote"]
    needs_sponsorship: bool
    industries: list[str] = field(default_factory=list)   # priority order
    schools: set[str] = field(default_factory=set)
    past_employers: set[str] = field(default_factory=set)
    proof_points: list[str] = field(default_factory=list)   # verified claims only
    facts: set[str] = field(default_factory=set)            # every claim the generator may make


@dataclass
class Job:
    id: str
    company: str
    title: str
    description: str
    location: str
    posted: date
    url: str = ""
    skills: set[str] = field(default_factory=set)
    industry: str = ""
    seniority_words: set[str] = field(default_factory=set)
    sponsorship: Sponsorship = Sponsorship.UNKNOWN
    company_sponsor_history: bool = False   # from public H1B disclosure data


@dataclass
class Contact:
    id: str
    job_id: str
    name: str
    title: str
    type: ContactType
    shared_hook: str = ""                    # the one specific reason to write
    has_email: bool = False
    has_public_activity: bool = False        # blog, talk, repo — something to anchor on
    role_relevance: float = 0.5              # 0..1, how close to the hiring decision


@dataclass
class Message:
    contact_id: str
    channel: Channel
    subject: str
    body: str
    hook_entities: set[str] = field(default_factory=set)   # named things about THEM used in the text
    claims: set[str] = field(default_factory=set)           # things asserted about the candidate


@dataclass
class Outcome:
    """Ground truth that closes the loop. One row per job the candidate acted on."""
    job_id: str
    features: dict[str, float]
    applied: bool
    replied: bool = False
    interview: bool = False
    offer: bool = False

    @property
    def label(self) -> int:
        return int(self.interview or self.offer)
