"""Contract tests for the adapter around the reviewed AI package.

The real ``ai.*`` package is contributed by its own pull request, so it is not
present here.  These tests install a **stub** that implements only the public
interface documented in ``docs/contributor-actions.md``:

    ai.graph.run_workflow(operation, request, provider, checkpointer=None, thread_id=None)
    ai.providers.create_provider(settings) / ai.providers.ProviderError
    ai.scoring.rule_based.calculate_lead_score(lead, weights=None,
                                               qualified_threshold=70, nurture_threshold=45)
    utils.config.get_settings(overrides=None)

The stub is written for this test; it is not a copy of the reviewed package and
does not assert anything about that package's internals.  It verifies the part
the backend owns: which operation is called, what payload is sent, and that
every returned value is validated against ``backend.intelligence.contract``.

When the real package lands, these tests keep working and become the first
smoke test of the real integration.
"""
from __future__ import annotations

import sys
import textwrap

import pytest

from backend.config import Settings
from backend.intelligence.contract import IntelligenceError
from backend.intelligence.external import ExternalAIEngine

GRAPH_STUB = '''
"""Test stub for the documented AI graph interface."""
from types import SimpleNamespace

CALLS = []
MODE = {"errors": [], "result": None, "research": None, "qualification": None}


def run_workflow(operation, request, provider, checkpointer=None, thread_id=None):
    CALLS.append({"operation": operation, "request": request})
    return SimpleNamespace(
        result=MODE["result"],
        research=MODE["research"],
        qualification=MODE["qualification"],
        execution=SimpleNamespace(
            operation=operation, provider="stub", model="stub-model",
            duration_ms=1, success=not MODE["errors"], used_mock=True,
        ),
        errors=list(MODE["errors"]),
    )
'''

PROVIDERS_STUB = '''
"""Test stub for the documented provider interface."""


class ProviderError(RuntimeError):
    pass


class _StubProvider:
    name = "stub"


def create_provider(settings):
    return _StubProvider()
'''

SCORING_STUB = '''
"""Test stub for the documented rule-based scorer."""
CALLS = []


def calculate_lead_score(lead, weights=None, qualified_threshold=70, nurture_threshold=45):
    CALLS.append({
        "lead": lead,
        "qualified_threshold": qualified_threshold,
        "nurture_threshold": nurture_threshold,
    })
    return {
        "score": 72,
        "qualification_category": "Qualified",
        "factors": [
            {
                "name": "Company fit",
                "weight": 100.0,
                "normalized_value": 0.72,
                "points": 72.0,
                "explanation": "stub factor",
                "signal": "positive",
            }
        ],
        "recommended_next_action": "Book a discovery call.",
    }
'''

CONFIG_STUB = '''
"""Test stub for the documented AI settings loader."""
CALLS = []


def get_settings(overrides=None):
    CALLS.append(overrides)
    return {"overrides": overrides}
'''

LEAD = {
    "id": "1",
    "company_name": "Acme Systems",
    "industry": "Software",
    "contact_name": "Dana Scully",
    "user_research": "Met at a conference.",
}


def _settings(**overrides) -> Settings:
    values = {"ai_backend": "external", "jwt_secret": "x" * 40}
    values.update(overrides)
    return Settings(**values)


@pytest.fixture()
def stub(tmp_path, monkeypatch):
    """Install the stub package on ``sys.path`` and reload it for this test."""
    root = tmp_path / "stubpkg"
    files = {
        "ai/__init__.py": "",
        "ai/graph.py": GRAPH_STUB,
        "ai/providers.py": PROVIDERS_STUB,
        "ai/scoring/__init__.py": "",
        "ai/scoring/rule_based.py": SCORING_STUB,
        "utils/__init__.py": "",
        "utils/config.py": CONFIG_STUB,
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")

    monkeypatch.syspath_prepend(str(root))
    for name in [key for key in sys.modules if key == "ai" or key.startswith("ai.")]:
        monkeypatch.delitem(sys.modules, name, raising=False)
    for name in [key for key in sys.modules if key == "utils" or key.startswith("utils.")]:
        monkeypatch.delitem(sys.modules, name, raising=False)

    import ai.graph
    import ai.scoring.rule_based
    import utils.config

    yield {
        "graph": ai.graph,
        "scoring": ai.scoring.rule_based,
        "config": utils.config,
    }

    # Modules imported during the test are not tracked by monkeypatch, so they
    # must be removed explicitly or later tests would see a "real" ai package.
    for name in [
        key
        for key in sys.modules
        if key == "ai" or key.startswith("ai.") or key == "utils" or key.startswith("utils.")
    ]:
        sys.modules.pop(name, None)


def test_engine_constructs_from_the_documented_interface(stub):
    engine = ExternalAIEngine(_settings(ai_provider="mock"))
    assert engine.name == "external"
    assert engine.provider == "stub"
    overrides = stub["config"].CALLS[-1]
    assert overrides["llm_provider"] == "mock"
    assert overrides["demo_mode"] is True


def test_analyze_lead_uses_lead_intelligence_and_injects_qualification(stub):
    stub["graph"].MODE.update(
        {
            "research": {
                "company_overview": "Stub overview.",
                "product_industry_fit": "Fits.",
                "buyer_role_relevance": "Relevant.",
            },
            "qualification": {
                "category": "Qualified",
                "fit_assessment": "Good fit.",
                "buyer_relevance": "Decision maker.",
                "engagement_assessment": "Engaged.",
                "recommended_next_step": "Book a call.",
            },
        }
    )
    engine = ExternalAIEngine(_settings())

    result, info = engine.analyze_lead(LEAD)

    call = stub["graph"].CALLS[-1]
    assert call["operation"] == "lead_intelligence"
    assert call["request"] == {"lead": LEAD}
    assert result.qualification.category == "Qualified"
    assert result.company_overview == "Stub overview."
    assert info.engine == "external"
    assert info.used_mock is True


@pytest.mark.parametrize(
    ("outreach_type", "channel"),
    [
        ("cold_email", "Email"),
        ("follow_up", "Email"),
        ("linkedin_message", "LinkedIn"),
        ("call_script", "Call script"),
        ("short_message", "Short message"),
    ],
)
def test_outreach_request_is_translated_to_the_package_keys(stub, outreach_type, channel):
    stub["graph"].MODE["result"] = {
        "channel": channel,
        "subject_line": "Subject",
        "body": "Body text.",
        "call_to_action": "Interested?",
    }
    engine = ExternalAIEngine(_settings())

    draft, _ = engine.generate_outreach(
        LEAD,
        {
            "tone": "formal",
            "length": "short",
            "outreach_type": outreach_type,
            "goal": "book a discovery call",
            "industry": "Software",
            "pain_points": ["manual reporting"],
            "product_service": "SalesGenie AI",
            "call_to_action": "Interested?",
        },
    )

    request = stub["graph"].CALLS[-1]["request"]
    assert stub["graph"].CALLS[-1]["operation"] == "outreach"
    assert request["lead"] is LEAD
    assert request["channel"] == channel
    assert request["campaign_objective"] == "book a discovery call"
    assert request["tone"] == "formal"
    assert "manual reporting" in request["company_insights"]
    assert "Met at a conference." in request["company_insights"]
    # Frontend-only keys must not leak into the package request.
    for key in ("outreach_type", "goal", "pain_points", "length"):
        assert key not in request
    assert draft.channel == channel


def test_score_lead_forwards_thresholds_and_never_invents_probability(stub):
    engine = ExternalAIEngine(
        _settings(score_threshold_qualified=80, score_threshold_nurture=50)
    )

    result, info = engine.score_lead(LEAD)

    call = stub["scoring"].CALLS[-1]
    assert call["qualified_threshold"] == 80
    assert call["nurture_threshold"] == 50
    assert result.score == 72
    assert result.conversion_probability is None
    assert info.model == "rule-based"


def test_package_errors_become_intelligence_errors(stub):
    stub["graph"].MODE["errors"] = ["provider unavailable"]
    engine = ExternalAIEngine(_settings())

    with pytest.raises(IntelligenceError, match="provider unavailable"):
        engine.recommend(LEAD)


def test_invalid_package_output_is_rejected(stub):
    stub["graph"].MODE["result"] = {"channel": "Email", "body": ""}
    engine = ExternalAIEngine(_settings())

    with pytest.raises(IntelligenceError):
        engine.generate_outreach(LEAD, {"outreach_type": "cold_email"})
