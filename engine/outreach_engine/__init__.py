"""Outreach Engine — the decision core of a job-search outreach product.

Four components, each independently testable:
  ranking       which jobs are worth a candidate's time (learns from outcomes)
  contacts      who to write to first for a given job
  quality_gate  whether a drafted message is good enough to send
  sequence      when to send, when to follow up, when to stop
  hooks         mine rare, recent, sourced facts about the reader to anchor on
  bandit        learn which message angle gets replies, per cohort
  planner       spend the user's daily budget on expected interviews, not volume
  replies       classify replies and decide the next action
Generation (the LLM call) is deliberately thin: the value is in what
surrounds it, not the prompt.
"""
from .models import Candidate, Job, Contact, Message, Outcome
from .ranking import JobFitRanker
from .contacts import ContactPrioritizer
from .quality_gate import MessageQualityGate
from .sequence import SequenceEngine
from .hooks import HookMiner, Hook
from .bandit import AngleBandit, Arm
from .planner import DailyPlanner, RecipientLedger
from .replies import classify as classify_reply, ReplyKind, next_action
