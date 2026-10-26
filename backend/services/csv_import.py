"""Transactional CSV lead import.

Design notes
------------
* The whole upload is validated before anything is written where possible, and
  every row is written inside a SAVEPOINT so a single bad row cannot leave a
  half-applied batch behind (the previous implementation called
  ``db.rollback()`` mid-loop, which discarded earlier rows and then raised).
* Duplicate policy is identical to the manual-create path (see
  ``backend.services.leads.find_duplicate``): normalised e-mail first, then
  company + contact name.
* The report always tells the caller exactly which rows were rejected and why.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.db import Lead
from backend.schemas import ImportReport, ImportRowError, normalise_stage
from backend.services.leads import email_key_for, find_duplicate, normalise_email

#: Accepted header aliases (all compared lower-case, spaces stripped).
HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "company_name": ("company_name", "company", "company name", "account name", "account"),
    "contact_name": ("contact_name", "contact name", "contact", "name", "full name"),
    "email": ("email", "e-mail", "email address", "work email"),
    "phone": ("phone", "phone number", "mobile", "telephone"),
    "website": ("website", "url", "company website", "domain"),
    "industry": ("industry", "sector", "vertical"),
    "company_size": ("company_size", "company size", "employees", "headcount"),
    "company_description": ("company_description", "description", "about", "company description"),
    "prospect_role": ("prospect_role", "role", "title", "job title", "prospect role"),
    "explicit_needs": ("explicit_needs", "needs", "business need", "explicit needs"),
    "pain_points": ("pain_points", "pain points", "challenges"),
    "lead_source": ("lead_source", "source", "lead source"),
    "stage": ("stage", "status", "lifecycle stage"),
}

MAX_FIELD_LENGTHS: dict[str, int] = {
    "company_name": 240,
    "contact_name": 200,
    "email": 320,
    "phone": 80,
    "website": 500,
    "industry": 160,
    "company_size": 100,
    "company_description": 8000,
    "prospect_role": 120,
    "explicit_needs": 8000,
    "pain_points": 8000,
    "lead_source": 120,
}

_REQUIRED_HEADER_GROUPS = ("company_name",)


class ImportValidationError(ValueError):
    """Raised when the file itself is unusable (extension, encoding, headers)."""


def _map_headers(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise ImportValidationError("CSV file has no header row.")
    lookup = {str(name or "").strip().lower(): str(name) for name in fieldnames}
    mapping: dict[str, str] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in lookup:
                mapping[canonical] = lookup[alias]
                break
    for required in _REQUIRED_HEADER_GROUPS:
        if required not in mapping:
            raise ImportValidationError(
                "CSV must contain a company name column "
                "(company_name, company, company name or account name)."
            )
    return mapping


def _decode(content: bytes, settings: Settings) -> str:
    if len(content) > settings.max_csv_bytes:
        raise ImportValidationError(
            f"CSV exceeds the {settings.max_csv_bytes // 1_000_000} MB upload limit."
        )
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportValidationError("CSV must be UTF-8 encoded.") from exc


def _clean_row(raw: dict[str, Any], mapping: dict[str, str]) -> dict[str, str]:
    row: dict[str, str] = {}
    for canonical, source in mapping.items():
        value = raw.get(source)
        row[canonical] = str(value).strip() if value is not None else ""
    return row


def _validate_row(row: dict[str, str], row_number: int) -> list[str]:
    errors: list[str] = []
    if not row.get("company_name"):
        errors.append("company_name is required")
    for field, limit in MAX_FIELD_LENGTHS.items():
        if len(row.get(field, "")) > limit:
            errors.append(f"{field} exceeds {limit} characters")
    email = normalise_email(row.get("email"))
    if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
        errors.append("email is not a valid address")
    return errors


def import_leads(
    db: Session, filename: str | None, content: bytes, settings: Settings
) -> ImportReport:
    if filename and not filename.lower().endswith(".csv"):
        raise ImportValidationError("Only .csv files are accepted.")

    text = _decode(content, settings)
    reader = csv.DictReader(io.StringIO(text))
    mapping = _map_headers(reader.fieldnames)

    imported = 0
    duplicates = 0
    invalid = 0
    total_rows = 0
    errors: list[ImportRowError] = []
    duplicate_rows: list[int] = []
    seen_emails: dict[str, int] = {}
    seen_company_contact: dict[tuple[str, str], int] = {}

    for row_number, raw in enumerate(reader, start=2):
        total_rows += 1
        if total_rows > settings.max_csv_rows:
            raise ImportValidationError(
                f"CSV exceeds the {settings.max_csv_rows} row limit."
            )

        row = _clean_row(raw, mapping)
        row_errors = _validate_row(row, row_number)
        if row_errors:
            invalid += 1
            errors.append(ImportRowError(row=row_number, error="; ".join(row_errors)))
            continue

        email = normalise_email(row.get("email"))
        company = " ".join(row["company_name"].split()).lower()
        contact = " ".join(row.get("contact_name", "").split()).lower()

        duplicate_reason: str | None = None
        if email and email in seen_emails:
            duplicate_reason = f"duplicate email within file (row {seen_emails[email]})"
        elif company and contact and (company, contact) in seen_company_contact:
            duplicate_reason = (
                "duplicate company+contact within file "
                f"(row {seen_company_contact[(company, contact)]})"
            )
        else:
            existing, reason = find_duplicate(
                db, email=email, company_name=company, contact_name=contact
            )
            if existing is not None:
                duplicate_reason = f"{reason} already belongs to lead {existing.id}"

        if duplicate_reason:
            duplicates += 1
            duplicate_rows.append(row_number)
            errors.append(ImportRowError(row=row_number, error=duplicate_reason))
            continue

        stage = "prospecting"
        if row.get("stage"):
            try:
                stage = normalise_stage(row["stage"])
            except ValueError as exc:
                invalid += 1
                errors.append(ImportRowError(row=row_number, error=str(exc)))
                continue

        try:
            with db.begin_nested():
                lead = Lead(
                    company_name=row["company_name"],
                    contact_name=row.get("contact_name", ""),
                    email=email,
                    email_key=email or None,
                    phone=row.get("phone", ""),
                    website=row.get("website", ""),
                    industry=row.get("industry", ""),
                    company_size=row.get("company_size", ""),
                    company_description=row.get("company_description", ""),
                    prospect_role=row.get("prospect_role", ""),
                    explicit_needs=row.get("explicit_needs", ""),
                    pain_points=row.get("pain_points", ""),
                    lead_source=row.get("lead_source", ""),
                    lifecycle_stage=stage,
                )
                db.add(lead)
                db.flush()
        except SQLAlchemyError as exc:
            invalid += 1
            errors.append(ImportRowError(row=row_number, error=f"database error: {exc.__class__.__name__}"))
            continue

        imported += 1
        if email:
            seen_emails[email] = row_number
        if company and contact:
            seen_company_contact[(company, contact)] = row_number

    db.commit()

    return ImportReport(
        filename=filename or "",
        imported=imported,
        duplicates=duplicates,
        invalid=invalid,
        total_rows=total_rows,
        errors=errors[:200],
        duplicate_rows=duplicate_rows,
    )
