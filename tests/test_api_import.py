"""CSV import validation, duplicate handling and reporting tests."""
from __future__ import annotations

import csv
import io


def _csv_bytes(rows: list[dict[str, str]], header: list[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _upload(client, headers, content: bytes, filename: str = "leads.csv"):
    return client.post(
        "/api/v1/leads/import",
        headers=headers,
        files={"file": (filename, content, "text/csv")},
    )


def test_import_happy_path_creates_leads(client, rep):
    header = ["company_name", "contact_name", "email", "industry", "stage"]
    content = _csv_bytes(
        [
            {
                "company_name": "Northwind Logistics",
                "contact_name": "Ada Fernandes",
                "email": "ada@northwind.test",
                "industry": "Logistics",
                "stage": "discovery",
            },
            {
                "company_name": "Contoso Manufacturing",
                "contact_name": "Lee Chan",
                "email": "lee@contoso.test",
                "industry": "Manufacturing",
                "stage": "qualified",
            },
        ],
        header,
    )
    response = _upload(client, rep, content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 2
    assert body["duplicates"] == 0
    assert body["invalid"] == 0
    assert body["total_rows"] == 2
    assert body["errors"] == []

    listed = client.get("/api/v1/leads", headers=rep)
    assert listed.headers["X-Total-Count"] == "2"
    stages = {item["company_name"]: item["stage"] for item in listed.json()}
    assert stages["Northwind Logistics"] == "discovery"
    assert stages["Contoso Manufacturing"] == "qualified"


def test_import_accepts_header_aliases(client, rep):
    content = _csv_bytes(
        [{"Company": "Alias Corp", "Email Address": "alias@corp.test"}],
        ["Company", "Email Address"],
    )
    response = _upload(client, rep, content)
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 1
    lead = client.get("/api/v1/leads", headers=rep).json()[0]
    assert lead["company_name"] == "Alias Corp"
    assert lead["email"] == "alias@corp.test"


def test_import_duplicate_email_within_file_is_reported(client, rep):
    header = ["company_name", "email"]
    content = _csv_bytes(
        [
            {"company_name": "One", "email": "same@dup.test"},
            {"company_name": "Two", "email": "SAME@dup.test"},
        ],
        header,
    )
    response = _upload(client, rep, content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 1
    assert body["duplicates"] == 1
    assert body["duplicate_rows"] == [3]
    assert "duplicate email within file" in body["errors"][0]["error"]


def test_import_duplicate_against_database_is_reported(client, lead, rep):
    content = _csv_bytes(
        [{"company_name": "Acme Systems", "email": "dana@acme.test"}],
        ["company_name", "email"],
    )
    response = _upload(client, rep, content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 0
    assert body["duplicates"] == 1
    assert lead["id"] in body["errors"][0]["error"]


def test_import_reports_invalid_rows_and_keeps_valid_ones(client, rep):
    header = ["company_name", "email"]
    content = _csv_bytes(
        [
            {"company_name": "", "email": "missing@company.test"},
            {"company_name": "Good Co", "email": "good@company.test"},
            {"company_name": "Bad Email", "email": "not-an-email"},
        ],
        header,
    )
    response = _upload(client, rep, content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 1
    assert body["invalid"] == 2
    assert body["total_rows"] == 3
    assert [item["row"] for item in body["errors"]] == [2, 4]
    assert "company_name is required" in body["errors"][0]["error"]
    assert "email is not a valid address" in body["errors"][1]["error"]
    # The valid row is committed; the invalid ones never were.
    assert client.get("/api/v1/leads", headers=rep).headers["X-Total-Count"] == "1"


def test_import_rejects_field_length_violations(client, rep):
    content = _csv_bytes(
        [{"company_name": "x" * 241, "email": "long@company.test"}],
        ["company_name", "email"],
    )
    response = _upload(client, rep, content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["invalid"] == 1
    assert "company_name exceeds 240 characters" in body["errors"][0]["error"]


def test_import_rejects_unknown_stage_per_row(client, rep):
    content = _csv_bytes(
        [
            {"company_name": "Bad Stage", "stage": "nonsense"},
            {"company_name": "Good Stage", "stage": "Closed Won"},
        ],
        ["company_name", "stage"],
    )
    response = _upload(client, rep, content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 1
    assert body["invalid"] == 1
    assert "Invalid lifecycle stage" in body["errors"][0]["error"]
    lead = client.get("/api/v1/leads", headers=rep).json()[0]
    assert lead["stage"] == "converted"


def test_import_rejects_non_csv_extension(client, rep):
    response = _upload(client, rep, b"company_name\nX\n", filename="leads.txt")
    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_file_type"


def test_import_rejects_empty_file(client, rep):
    response = _upload(client, rep, b"   ")
    assert response.status_code == 422
    assert response.json()["code"] == "empty_file"


def test_import_requires_company_column(client, rep):
    content = _csv_bytes([{"email": "x@y.test"}], ["email"])
    response = _upload(client, rep, content)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_csv"
    assert "company name column" in response.json()["detail"]


def test_import_rejects_non_utf8_content(client, rep):
    response = _upload(client, rep, b"company_name\n\xff\xfe\n")
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_csv"


def test_import_requires_write_role(client, viewer):
    content = _csv_bytes([{"company_name": "Nope"}], ["company_name"])
    response = _upload(client, viewer, content)
    assert response.status_code == 403
