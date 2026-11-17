"""Shared fixtures. Tests never hit the network: the LLM client is forced into
'unavailable' mode so every test exercises the deterministic heuristic path
(and, where relevant, the LLM-failure degradation path).
"""
from __future__ import annotations

import copy
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("SI_DATABASE_URL", None)

from sales_intel.ai.llm import client as llm_client  # noqa: E402
from sales_intel.config import DEFAULT_SCORING  # noqa: E402
from sales_intel.db import repository as repo_module  # noqa: E402
from sales_intel.schemas import (  # noqa: E402
    InteractionHistory,
    LeadContext,
    LeadFeatures,
    Utterance,
)

SAMPLE_DIR = ROOT / "data" / "sample"


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    """Force the no-provider path for every test."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    llm_client._default = None
    yield
    llm_client._default = None


@pytest.fixture(autouse=True)
def _fresh_repo():
    repo_module.reset_repository()
    yield
    repo_module.reset_repository()


@pytest.fixture
def scoring_config() -> dict:
    """Default (untuned) config — keeps scoring tests independent of artifacts."""
    return copy.deepcopy(DEFAULT_SCORING)


@pytest.fixture
def hot_lead() -> LeadFeatures:
    """A lead that should score Hot: high intent + readiness + fit."""
    return LeadFeatures(
        lead_id="L-HOT",
        company_name="Vertex Manufacturing Group",
        industry="Manufacturing",
        email_opens=16, email_clicks=6, email_replies=4, inbound_replies=3,
        meetings_held=3, call_connect_rate=0.75, avg_response_latency_hours=2.0,
        industry_match=0.95, company_size_score=0.9, seniority_score=0.9,
        tech_stack_overlap=0.85, budget_potential_usd=140_000,
        pricing_page_visits=8, demo_requests=3, content_downloads=5,
        hiring_signal=3, competitor_mention=2,
        budget_confirmed=1, timeline_months=2, stakeholders_identified=5,
        procurement_stage=3, champion_identified=1,
    )


@pytest.fixture
def cold_lead() -> LeadFeatures:
    return LeadFeatures(
        lead_id="L-COLD",
        company_name="Lumen Retail Labs",
        industry="Retail",
        email_opens=1, email_clicks=0, email_replies=0, inbound_replies=0,
        meetings_held=0, call_connect_rate=0.05, avg_response_latency_hours=70.0,
        industry_match=0.2, company_size_score=0.1, seniority_score=0.1,
        tech_stack_overlap=0.1, budget_potential_usd=6_000,
        pricing_page_visits=0, demo_requests=0, content_downloads=0,
        hiring_signal=0, competitor_mention=0,
        budget_confirmed=0, timeline_months=15, stakeholders_identified=0,
        procurement_stage=0, champion_identified=0,
    )


@pytest.fixture
def qualified_context() -> LeadContext:
    now = datetime(2026, 11, 5, 10, 0, 0)
    return LeadContext(
        lead_id="L-HOT",
        company_name="Vertex Manufacturing Group",
        industry="Manufacturing",
        lifecycle_stage="qualified",
        seniority="vp",
        decision_maker=True,
        deal_value_usd=85_000,
        last_contact_at=now - timedelta(days=5),
        local_hour=11,
        pain_points=["manual lead qualification", "slow follow-up"],
        industry_tags=["distributor network"],
        history=[
            InteractionHistory(channel="email", occurred_at=now - timedelta(days=12), outcome="opened"),
            InteractionHistory(channel="email", occurred_at=now - timedelta(days=9), outcome="replied"),
            InteractionHistory(channel="call", occurred_at=now - timedelta(days=5), outcome="positive"),
        ],
    )


@pytest.fixture
def labelled_leads() -> tuple[list[LeadFeatures], list[int]]:
    path = SAMPLE_DIR / "leads_labelled.json"
    if not path.exists():
        pytest.skip("sample dataset missing — run scripts/generate_sample_data.py")
    leads, labels = [], []
    for row in json.loads(path.read_text()):
        row = dict(row)
        labels.append(int(row.pop("converted")))
        leads.append(LeadFeatures(**row))
    return leads, labels


@pytest.fixture
def sales_call() -> list[Utterance]:
    base = datetime(2026, 11, 4, 15, 0, 0)
    lines = [
        ("Priya", "Thanks for making the time today. We wanted to walk through the pilot results.", True),
        ("Client", "Sure. The main thing we care about is whether this replaces our spreadsheet process.", False),
        ("Priya", "It does. We import your existing leads, score them and route the hot ones first.", True),
        ("Client", "Our concern is the price. It is higher than what we budgeted for this quarter.", False),
        ("Priya", "Understood. I'll send a revised quote by Friday with a smaller starter tier.", True),
        ("Client", "Please share the security documentation as well. Our CISO will review it before sign-off.", False),
        ("Client", "We talked to Salesforce but their setup was too heavy for our team.", False),
        ("Priya", "We'll set up a technical call next week to walk through the API and the HubSpot sync.", True),
        ("Client", "Sounds good. Rahul will own the security review on our side.", False),
        ("Priya", "Great. I will prepare the pilot summary deck for your leadership team by Monday.", True),
    ]
    return [Utterance(speaker=sp, text=tx, timestamp=base + timedelta(minutes=i * 3), is_internal=internal)
            for i, (sp, tx, internal) in enumerate(lines)]
