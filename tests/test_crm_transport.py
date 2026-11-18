"""Tests for the live CRM transport (Module 5).

No test opens a socket: the HTTP layer is replaced by a fake transport, and the
route tests monkeypatch ``transport_for``.  That is deliberate - a unit suite
must never contact a real Salesforce org or HubSpot portal.
"""
from __future__ import annotations

import json

import pytest

from backend.config import get_settings, reset_settings_cache
from backend.services.crm_transport import (
    CRMTransportError,
    HubSpotTransport,
    SalesforceTransport,
    credentials_present,
    hubspot_record,
    salesforce_record,
    send_with_retry,
    split_name,
    transport_for,
)


@pytest.fixture(autouse=True)
def fresh_settings():
    """Keep cached settings from leaking between tests."""
    reset_settings_cache()
    yield
    reset_settings_cache()


class FakeTransport:
    """A transport that returns or raises a scripted sequence of results."""

    provider = "salesforce"
    max_attempts = 3
    backoff_seconds = 0.0

    def __init__(self, results):
        self.results = list(results)
        self.calls: list[tuple[str, dict]] = []

    def send(self, record_type: str, payload: dict) -> dict:
        self.calls.append((record_type, payload))
        item = self.results.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


# ---------------------------------------------------------------------------
# Payload mapping
# ---------------------------------------------------------------------------
def test_split_name_never_invents_a_last_name():
    assert split_name("Ada Lovelace") == ("Ada", "Lovelace")
    assert split_name("Ada") == ("Ada", "")
    assert split_name("") == ("", "")


def test_salesforce_contact_maps_to_a_lead_with_required_fields():
    sobject, fields = salesforce_record(
        "contact",
        {
            "company_name": "Acme",
            "contact_name": "Ada Lovelace",
            "email": "ada@acme.test",
            "lifecycle_stage": "qualified",
        },
    )
    assert sobject == "Lead"
    assert fields["Company"] == "Acme"
    assert fields["LastName"] == "Lovelace"
    assert fields["FirstName"] == "Ada"
    assert fields["Status"] == "Working - Contacted"
    # Empty optional values are omitted rather than sent as blank strings.
    assert "Phone" not in fields


def test_salesforce_contact_rejects_a_missing_required_field():
    with pytest.raises(CRMTransportError) as excinfo:
        salesforce_record("contact", {"company_name": "Acme", "contact_name": ""})
    assert excinfo.value.retryable is False
    assert "LastName" in str(excinfo.value)


def test_salesforce_deal_and_activity_shapes():
    sobject, fields = salesforce_record(
        "deal", {"company_name": "Acme", "lifecycle_stage": "proposal"}
    )
    assert sobject == "Opportunity"
    assert fields["StageName"] == "Proposal/Price Quote"
    assert fields["Name"] == "Acme"
    assert "CloseDate" in fields

    sobject, fields = salesforce_record(
        "activity", {"company_name": "Acme", "contact_name": "Ada Lovelace"}
    )
    assert sobject == "Task"
    assert fields["Subject"]
    assert fields["Status"] == "Completed"


def test_hubspot_contact_and_deal_shapes():
    object_type, properties = hubspot_record(
        "contact",
        {
            "company_name": "Acme",
            "contact_name": "Ada Lovelace",
            "email": "ada@acme.test",
            "lifecycle_stage": "converted",
        },
    )
    assert object_type == "contacts"
    assert properties["lastname"] == "Lovelace"
    assert properties["lifecyclestage"] == "customer"
    assert properties["email"] == "ada@acme.test"

    object_type, properties = hubspot_record(
        "deal", {"company_name": "Acme", "lifecycle_stage": "negotiation"}
    )
    assert object_type == "deals"
    assert properties["dealstage"] == "contractsent"


def test_unknown_record_type_is_refused():
    with pytest.raises(CRMTransportError):
        salesforce_record("invoice", {"company_name": "Acme"})
    with pytest.raises(CRMTransportError):
        hubspot_record("invoice", {"company_name": "Acme"})


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------
def test_transient_failure_is_retried_then_succeeds():
    transport = FakeTransport(
        [
            CRMTransportError("rate limited", retryable=True, retry_after=0.0),
            {"external_record_id": "sf-1", "http_status": 201},
        ]
    )
    result = send_with_retry(transport, "contact", {"company_name": "Acme"}, sleep=lambda _: None)
    assert result["external_record_id"] == "sf-1"
    assert result["attempts"] == 2
    assert len(transport.calls) == 2


def test_retry_stops_at_max_attempts():
    transport = FakeTransport(
        [CRMTransportError("gateway", retryable=True) for _ in range(FakeTransport.max_attempts)]
    )
    with pytest.raises(CRMTransportError) as excinfo:
        send_with_retry(transport, "contact", {}, sleep=lambda _: None)
    assert excinfo.value.attempts == FakeTransport.max_attempts


def test_non_retryable_failure_is_not_repeated():
    transport = FakeTransport([CRMTransportError("bad payload", retryable=False)])
    with pytest.raises(CRMTransportError) as excinfo:
        send_with_retry(transport, "contact", {}, sleep=lambda _: None)
    assert excinfo.value.attempts == 1
    assert len(transport.calls) == 1


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def test_live_transport_is_off_by_default():
    assert get_settings().crm_live_enabled is False
    assert transport_for("salesforce") is None
    assert transport_for("hubspot") is None
    assert credentials_present("salesforce") is False


def test_credentials_alone_do_not_enable_live_calls(monkeypatch):
    monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://example.my.salesforce.com")
    monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "token-value")
    reset_settings_cache()
    assert credentials_present("salesforce") is True
    assert transport_for("salesforce") is None


def test_flag_plus_credentials_builds_a_transport(monkeypatch):
    monkeypatch.setenv("CRM_LIVE_ENABLED", "true")
    monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://example.my.salesforce.com")
    monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "token-value")
    reset_settings_cache()
    transport = transport_for("salesforce")
    assert isinstance(transport, SalesforceTransport)
    assert transport.instance_url == "https://example.my.salesforce.com"

    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "hubspot-token")
    reset_settings_cache()
    assert isinstance(transport_for("hubspot"), HubSpotTransport)


# ---------------------------------------------------------------------------
# Route behaviour
# ---------------------------------------------------------------------------
def test_live_sync_writes_a_live_audit_row(client, lead, rep, db, monkeypatch):
    from backend.routers import analytics
    from backend.db import CRMSyncLog

    transport = FakeTransport([{"external_record_id": "00Q-1", "http_status": 201}])
    monkeypatch.setattr(analytics, "transport_for", lambda provider: transport)

    response = client.post(
        "/api/v1/crm/sync",
        headers=rep,
        json={
            "provider": "salesforce",
            "operation": "sync_contact",
            "lead_ids": [int(lead["id"])],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "live"
    assert body["simulated"] is False
    assert body["records"][0]["external_record_id"] == "00Q-1"

    log = db.query(CRMSyncLog).order_by(CRMSyncLog.id.desc()).first()
    assert log.status == "success"
    assert log.external_record_id == "00Q-1"
    assert log.request_metadata["mode"] == "live"
    # The credential must never reach the audit table.
    assert "token-value" not in json.dumps(log.request_metadata)
    assert transport.calls[0][0] == "contact"


def test_live_failure_is_audited_and_returns_502(client, lead, rep, db, monkeypatch):
    from backend.routers import analytics
    from backend.db import CRMSyncLog

    transport = FakeTransport(
        [CRMTransportError("bad payload", provider="salesforce", status_code=400)]
    )
    monkeypatch.setattr(analytics, "transport_for", lambda provider: transport)

    response = client.post(
        "/api/v1/crm/sync",
        headers=rep,
        json={"provider": "salesforce", "operation": "sync_contact", "lead_ids": [lead["id"]]},
    )
    assert response.status_code == 502, response.text
    assert response.json()["code"] == "crm_sync_failed"

    log = db.query(CRMSyncLog).order_by(CRMSyncLog.id.desc()).first()
    assert log.status == "failed"
    assert log.response_metadata["mode"] == "live"
    assert log.attempt_count == 1


def test_unconfigured_sync_still_returns_501(client, lead, rep, db):
    from backend.db import CRMSyncLog

    response = client.post(
        "/api/v1/crm/sync",
        headers=rep,
        json={"provider": "salesforce", "operation": "sync_contact", "lead_ids": [lead["id"]]},
    )
    assert response.status_code == 501
    log = db.query(CRMSyncLog).order_by(CRMSyncLog.id.desc()).first()
    assert log.request_metadata["mode"] == "not_configured"


def test_providers_report_live_availability(client, rep, monkeypatch):
    from backend.routers import analytics

    fake = FakeTransport([])
    monkeypatch.setattr(
        analytics,
        "transport_for",
        lambda provider: fake if provider == "salesforce" else None,
    )
    response = client.get("/api/v1/crm/providers", headers=rep)
    providers = {row["provider"]: row for row in response.json()}
    assert providers["salesforce"]["live_sync_available"] is True
    assert providers["hubspot"]["live_sync_available"] is False
