"""Live CRM transports for Salesforce and HubSpot.

The canonical backend ships a provider-neutral payload mapper and a
deterministic simulator (``backend.services.crm``).  This module adds the
transport that the simulator deliberately left out: real HTTP calls to a
Salesforce org or a HubSpot portal when credentials are configured.

Design rules:

* **Off by default.**  A live call only happens when ``CRM_LIVE_ENABLED=true``
  *and* the provider credentials are present.  A demo machine with a token in
  ``.env`` still runs the simulator unless the flag is set, so a test or demo
  cannot accidentally mutate a real CRM.
* **No secrets in logs.**  Tokens are only placed in the request header.  The
  audit metadata written by the API contains the payload and the HTTP status,
  never the credential.
* **Retry only what is safe.**  ``429`` and ``5xx`` are retried with
  exponential backoff (honouring ``Retry-After``); ``4xx`` validation errors
  fail immediately.
* **Stdlib only.**  ``urllib.request`` keeps the runtime dependency set
  unchanged, so the Docker image does not need a new package.

The field maps are configurable at the edges but default to documented vendor
names.  They have not been confirmed against a real org (SRS D-06); a CRM
administrator must confirm custom fields before a production rollout.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Protocol

from backend.config import get_settings

#: Canonical operation -> CRM record type (kept in step with services.crm).
RECORD_TYPES = ("contact", "activity", "deal")


class CRMTransportError(Exception):
    """A CRM call failed.

    ``retryable`` distinguishes a transient provider problem (rate limit,
    gateway error, timeout) from a payload or authentication problem that will
    fail again if repeated.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        status_code: int | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
        attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after = retry_after
        self.attempts = attempts


class LiveTransport(Protocol):
    provider: str
    max_attempts: int
    backoff_seconds: float

    def send(self, record_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create one record and return ``{"external_record_id", "http_status"}``."""


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------
_SALESFORCE_OBJECT = {"contact": "Lead", "activity": "Task", "deal": "Opportunity"}

#: Canonical lifecycle stage -> Salesforce Lead status / Opportunity stage.
_SALESFORCE_LEAD_STATUS = {
    "prospecting": "Open - Not Contacted",
    "discovery": "Working - Contacted",
    "qualified": "Working - Contacted",
    "proposal": "Working - Contacted",
    "negotiation": "Working - Contacted",
    "converted": "Closed - Converted",
    "lost": "Closed - Not Converted",
}
_SALESFORCE_OPPORTUNITY_STAGE = {
    "prospecting": "Prospecting",
    "discovery": "Qualification",
    "qualified": "Needs Analysis",
    "proposal": "Proposal/Price Quote",
    "negotiation": "Negotiation/Review",
    "converted": "Closed Won",
    "lost": "Closed Lost",
}

_HUBSPOT_OBJECT = {"contact": "contacts", "activity": "tasks", "deal": "deals"}
_HUBSPOT_LIFECYCLE = {
    "prospecting": "lead",
    "discovery": "marketingqualifiedlead",
    "qualified": "salesqualifiedlead",
    "proposal": "opportunity",
    "negotiation": "opportunity",
    "converted": "customer",
    "lost": "other",
}
_HUBSPOT_DEAL_STAGE = {
    "prospecting": "appointmentscheduled",
    "discovery": "qualifiedtobuy",
    "qualified": "presentationscheduled",
    "proposal": "decisionmakerboughtin",
    "negotiation": "contractsent",
    "converted": "closedwon",
    "lost": "closedlost",
}


def split_name(full_name: str | None) -> tuple[str, str]:
    """Split a display name into ``(first, last)`` without inventing a value."""
    parts = str(full_name or "").strip().split(None, 1)
    if not parts:
        return "", ""
    return parts[0], parts[1] if len(parts) > 1 else ""


def _present(values: dict[str, Any]) -> dict[str, Any]:
    """Drop empty values so a CRM does not receive blank strings for unset fields."""
    return {
        key: value
        for key, value in values.items()
        if value not in (None, "", [], {})
    }


def salesforce_record(record_type: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Map a provider-neutral record onto a Salesforce object and field set."""
    company = str(payload.get("company_name") or "").strip()
    first, last = split_name(payload.get("contact_name"))
    stage = str(payload.get("lifecycle_stage") or "prospecting").lower()

    if record_type == "contact":
        if not company or not last:
            raise CRMTransportError(
                "Salesforce requires Company and LastName; the lead is missing "
                "company_name or contact_name.",
                provider="salesforce",
                retryable=False,
            )
        fields = _present(
            {
                "Company": company,
                "LastName": last,
                "FirstName": first,
                "Email": payload.get("email"),
                "Phone": payload.get("phone"),
                "Website": payload.get("website"),
                "Industry": payload.get("industry"),
                "NumberOfEmployees": payload.get("company_size"),
                "AnnualRevenue": payload.get("annual_revenue"),
                "Status": _SALESFORCE_LEAD_STATUS.get(stage, "Open - Not Contacted"),
                "OwnerId": payload.get("owner_id"),
            }
        )
        return _SALESFORCE_OBJECT["contact"], fields

    if record_type == "activity":
        description = " | ".join(
            part
            for part in (
                str(payload.get("activity") or "SalesGenie lead synchronisation"),
                f"Company: {company}" if company else "",
                f"Contact: {payload.get('contact_name')}" if payload.get("contact_name") else "",
            )
            if part
        )
        fields = _present(
            {
                "Subject": "SalesGenie lead synchronisation",
                "Status": "Completed",
                "Priority": "Normal",
                "ActivityDate": date.today().isoformat(),
                "Description": description,
            }
        )
        return _SALESFORCE_OBJECT["activity"], fields

    if record_type == "deal":
        if not company:
            raise CRMTransportError(
                "Salesforce requires an Opportunity Name; the lead is missing company_name.",
                provider="salesforce",
                retryable=False,
            )
        fields = _present(
            {
                "Name": company,
                "StageName": _SALESFORCE_OPPORTUNITY_STAGE.get(stage, "Prospecting"),
                "Amount": payload.get("annual_revenue"),
                "CloseDate": (date.today() + timedelta(days=30)).isoformat(),
                "LeadSource": "SalesGenie AI",
            }
        )
        return _SALESFORCE_OBJECT["deal"], fields

    raise CRMTransportError(
        f"Unsupported CRM record type: {record_type!r}.", provider="salesforce"
    )


def hubspot_record(record_type: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Map a provider-neutral record onto a HubSpot object and properties."""
    company = str(payload.get("company_name") or "").strip()
    first, last = split_name(payload.get("contact_name"))
    stage = str(payload.get("lifecycle_stage") or "prospecting").lower()

    if record_type == "contact":
        if not last:
            raise CRMTransportError(
                "HubSpot requires a last name; the lead is missing contact_name.",
                provider="hubspot",
                retryable=False,
            )
        properties = _present(
            {
                "company": company,
                "firstname": first,
                "lastname": last,
                "email": payload.get("email"),
                "phone": payload.get("phone"),
                "website": payload.get("website"),
                "industry": payload.get("industry"),
                "numberofemployees": payload.get("company_size"),
                "annualrevenue": payload.get("annual_revenue"),
                "lifecyclestage": _HUBSPOT_LIFECYCLE.get(stage, "lead"),
                "hubspot_owner_id": payload.get("owner_id"),
            }
        )
        return _HUBSPOT_OBJECT["contact"], properties

    if record_type == "activity":
        body = " | ".join(
            part
            for part in (
                str(payload.get("activity") or "SalesGenie lead synchronisation"),
                f"Company: {company}" if company else "",
                f"Contact: {payload.get('contact_name')}" if payload.get("contact_name") else "",
            )
            if part
        )
        properties = _present(
            {
                "hs_task_subject": "SalesGenie lead synchronisation",
                "hs_task_body": body,
                "hs_task_status": "COMPLETED",
                "hs_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return _HUBSPOT_OBJECT["activity"], properties

    if record_type == "deal":
        if not company:
            raise CRMTransportError(
                "HubSpot requires a deal name; the lead is missing company_name.",
                provider="hubspot",
                retryable=False,
            )
        properties = _present(
            {
                "dealname": company,
                "dealstage": _HUBSPOT_DEAL_STAGE.get(stage, "appointmentscheduled"),
                "amount": payload.get("annual_revenue"),
                "closedate": (date.today() + timedelta(days=30)).isoformat(),
            }
        )
        return _HUBSPOT_OBJECT["deal"], properties

    raise CRMTransportError(
        f"Unsupported CRM record type: {record_type!r}.", provider="hubspot"
    )


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------
def _safe_detail(raw: str, limit: int = 300) -> str:
    """Trim a provider error body so it cannot flood the audit log."""
    text = " ".join(str(raw or "").split())
    return text[:limit]


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None,
    timeout: float,
) -> tuple[int, dict[str, Any]]:
    """Perform one JSON request with ``urllib`` and return ``(status, body)``.

    Kept as a module-level function so tests can replace it without opening a
    socket.  Every failure becomes a :class:`CRMTransportError`.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8") or "{}"
            return int(response.status), json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        retry_after: float | None = None
        header = exc.headers.get("Retry-After") if exc.headers else None
        if header:
            try:
                retry_after = float(header)
            except ValueError:
                retry_after = None
        raise CRMTransportError(
            f"CRM returned HTTP {exc.code}: {_safe_detail(raw)}",
            status_code=int(exc.code),
            retryable=int(exc.code) == 429 or 500 <= int(exc.code) < 600,
            retry_after=retry_after,
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CRMTransportError(
            f"CRM request failed: {type(exc).__name__}",
            retryable=True,
        ) from exc


@dataclass
class SalesforceTransport:
    instance_url: str
    access_token: str
    api_version: str = "60.0"
    timeout_seconds: float = 10.0
    max_attempts: int = 3
    backoff_seconds: float = 0.5
    provider: str = "salesforce"

    def _url(self, sobject: str) -> str:
        base = self.instance_url.rstrip("/")
        return f"{base}/services/data/v{self.api_version}/sobjects/{sobject}/"

    def send(self, record_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        sobject, fields = salesforce_record(record_type, payload)
        status, body = http_json(
            "POST",
            self._url(sobject),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=fields,
            timeout=self.timeout_seconds,
        )
        if body.get("success") is False:
            raise CRMTransportError(
                f"Salesforce rejected the record: {_safe_detail(json.dumps(body.get('errors')))}",
                provider=self.provider,
                status_code=status,
                retryable=False,
            )
        record_id = str(body.get("id") or "")
        if not record_id:
            raise CRMTransportError(
                "Salesforce accepted the request but returned no record id.",
                provider=self.provider,
                status_code=status,
                retryable=False,
            )
        return {"external_record_id": record_id, "http_status": status}


@dataclass
class HubSpotTransport:
    access_token: str
    base_url: str = "https://api.hubapi.com"
    timeout_seconds: float = 10.0
    max_attempts: int = 3
    backoff_seconds: float = 0.5
    provider: str = "hubspot"

    def _url(self, object_type: str) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/crm/v3/objects/{object_type}"

    def send(self, record_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        object_type, properties = hubspot_record(record_type, payload)
        status, body = http_json(
            "POST",
            self._url(object_type),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body={"properties": properties},
            timeout=self.timeout_seconds,
        )
        record_id = str(body.get("id") or "")
        if not record_id:
            raise CRMTransportError(
                "HubSpot accepted the request but returned no object id.",
                provider=self.provider,
                status_code=status,
                retryable=False,
            )
        return {"external_record_id": record_id, "http_status": status}


# ---------------------------------------------------------------------------
# Configuration and retry
# ---------------------------------------------------------------------------
def transport_for(provider: str) -> SalesforceTransport | HubSpotTransport | None:
    """Return a configured live transport, or ``None`` for the simulator path."""
    settings = get_settings()
    key = str(provider or "").strip().lower()
    if not settings.crm_live_enabled:
        return None
    if key == "salesforce":
        if not settings.salesforce_instance_url or not settings.salesforce_access_token:
            return None
        return SalesforceTransport(
            instance_url=settings.salesforce_instance_url,
            access_token=settings.salesforce_access_token,
            api_version=settings.salesforce_api_version,
            timeout_seconds=settings.crm_timeout_seconds,
            max_attempts=settings.crm_max_attempts,
            backoff_seconds=settings.crm_backoff_seconds,
        )
    if key == "hubspot":
        if not settings.hubspot_access_token:
            return None
        return HubSpotTransport(
            access_token=settings.hubspot_access_token,
            base_url=settings.hubspot_base_url,
            timeout_seconds=settings.crm_timeout_seconds,
            max_attempts=settings.crm_max_attempts,
            backoff_seconds=settings.crm_backoff_seconds,
        )
    return None


def credentials_present(provider: str) -> bool:
    """True when the provider has the credentials a live call would need."""
    settings = get_settings()
    key = str(provider or "").strip().lower()
    if key == "salesforce":
        return bool(settings.salesforce_instance_url and settings.salesforce_access_token)
    if key == "hubspot":
        return bool(settings.hubspot_access_token)
    return False


def send_with_retry(
    transport: LiveTransport,
    record_type: str,
    payload: dict[str, Any],
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Send one record, retrying transient failures with exponential backoff."""
    last: CRMTransportError | None = None
    for attempt in range(1, transport.max_attempts + 1):
        try:
            result = transport.send(record_type, payload)
            return {**result, "attempts": attempt}
        except CRMTransportError as exc:
            last = exc
            exc.attempts = attempt
            if not exc.retryable or attempt >= transport.max_attempts:
                break
            delay = (
                exc.retry_after
                if exc.retry_after is not None
                else transport.backoff_seconds * (2 ** (attempt - 1))
            )
            sleep(min(max(delay, 0.0), 30.0))
    assert last is not None
    raise last
