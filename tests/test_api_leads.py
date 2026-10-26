"""Lead CRUD, validation, lifecycle and authorisation tests."""
from __future__ import annotations

import pytest


def test_create_lead_returns_201_and_normalises_email(client, rep):
    response = client.post(
        "/api/v1/leads",
        headers=rep,
        json={"company_name": "  Northwind   Logistics ", "email": "ADA@Example.COM"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["company_name"] == "Northwind Logistics"
    assert body["email"] == "ada@example.com"
    assert body["stage"] == "prospecting"
    assert body["status"] == "New"
    assert isinstance(body["id"], str)


def test_create_lead_requires_company_name(client, rep):
    response = client.post("/api/v1/leads", headers=rep, json={"company_name": ""})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_create_lead_rejects_invalid_email(client, rep):
    response = client.post(
        "/api/v1/leads", headers=rep, json={"company_name": "Bad", "email": "nope"}
    )
    assert response.status_code == 422


def test_create_lead_rejects_invalid_stage(client, rep):
    response = client.post(
        "/api/v1/leads", headers=rep, json={"company_name": "Bad", "stage": "made-up"}
    )
    assert response.status_code == 422


def test_stage_aliases_are_accepted(client, rep):
    response = client.post(
        "/api/v1/leads", headers=rep, json={"company_name": "Alias Co", "stage": "Closed Won"}
    )
    assert response.status_code == 201, response.text
    assert response.json()["stage"] == "converted"
    assert response.json()["status"] == "Closed"


def test_duplicate_email_returns_409_with_match(client, lead, rep):
    response = client.post(
        "/api/v1/leads", headers=rep, json={"company_name": "Other", "email": "DANA@acme.test"}
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "duplicate_lead"
    assert body["meta"]["matched_lead_id"] == lead["id"]


def test_duplicate_company_and_contact_returns_409(client, lead, rep):
    response = client.post(
        "/api/v1/leads",
        headers=rep,
        json={"company_name": "Acme Systems", "contact_name": "Dana Scully"},
    )
    assert response.status_code == 409
    assert response.json()["meta"]["match_reason"] == "company+contact"


def test_duplicate_check_endpoint(client, lead, rep):
    hit = client.post(
        "/api/v1/leads/duplicate-check",
        headers=rep,
        json={"email": "dana@acme.test"},
    )
    assert hit.status_code == 200
    assert hit.json()["is_duplicate"] is True

    miss = client.post(
        "/api/v1/leads/duplicate-check",
        headers=rep,
        json={"email": "new@acme.test"},
    )
    assert miss.json()["is_duplicate"] is False


def test_get_and_list_leads_with_pagination_headers(client, rep):
    for index in range(3):
        client.post(
            "/api/v1/leads",
            headers=rep,
            json={"company_name": f"Company {index}", "industry": "Retail"},
        )
    client.post(
        "/api/v1/leads", headers=rep, json={"company_name": "Software Co", "industry": "Software"}
    )

    page = client.get("/api/v1/leads", headers=rep, params={"page": 1, "page_size": 2})
    assert page.status_code == 200
    assert len(page.json()) == 2
    assert page.headers["X-Total-Count"] == "4"
    assert page.headers["X-Page"] == "1"

    filtered = client.get("/api/v1/leads", headers=rep, params={"industry": "Software"})
    assert [item["company_name"] for item in filtered.json()] == ["Software Co"]

    searched = client.get("/api/v1/leads", headers=rep, params={"query": "Company 1"})
    assert len(searched.json()) == 1


def test_get_missing_lead_returns_404(client, rep):
    response = client.get("/api/v1/leads/9999", headers=rep)
    assert response.status_code == 404
    assert response.json()["code"] == "lead_not_found"


def test_patch_lead_updates_fields_and_stage(client, lead, rep):
    response = client.patch(
        f"/api/v1/leads/{lead['id']}",
        headers=rep,
        json={"stage": "proposal", "industry": "Enterprise Software"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stage"] == "proposal"
    assert body["status"] == "Active"
    assert body["industry"] == "Enterprise Software"
    # untouched fields survive a partial update
    assert body["contact_name"] == "Dana Scully"


def test_patch_lead_email_conflict_returns_409(client, lead, rep):
    other = client.post(
        "/api/v1/leads", headers=rep, json={"company_name": "Other Co", "email": "other@acme.test"}
    ).json()
    response = client.patch(
        f"/api/v1/leads/{other['id']}", headers=rep, json={"email": "dana@acme.test"}
    )
    assert response.status_code == 409


def test_delete_requires_manager_role(client, lead, rep, manager):
    forbidden = client.delete(f"/api/v1/leads/{lead['id']}", headers=rep)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"

    deleted = client.delete(f"/api/v1/leads/{lead['id']}", headers=manager)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/leads/{lead['id']}", headers=manager).status_code == 404


def test_viewer_cannot_create_leads(client, viewer):
    response = client.post("/api/v1/leads", headers=viewer, json={"company_name": "Nope"})
    assert response.status_code == 403


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/api/v1/leads").status_code == 401
    assert client.post("/api/v1/leads", json={"company_name": "Nope"}).status_code == 401


def test_unknown_query_stage_is_rejected(client, rep):
    response = client.get("/api/v1/leads", headers=rep, params={"stage": "bogus"})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_stage"


@pytest.mark.parametrize("field", ["company_name", "company_description", "tech_stack"])
def test_field_length_limits_are_enforced(client, rep, field):
    response = client.post(
        "/api/v1/leads", headers=rep, json={"company_name": "Ok", field: "x" * 9000}
    )
    assert response.status_code == 422
