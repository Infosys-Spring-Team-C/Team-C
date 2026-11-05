"""Operator CLI.

Examples
--------
Create the first administrator (prompts for the password, never echoes it)::

    python -m backend.cli create-user --email lead@example.com --role admin

Create the schema without Alembic (development only)::

    python -m backend.cli init-db

Seed a small set of clearly-labelled demo leads for a local demonstration::

    python -m backend.cli seed-demo --confirm
"""
from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from backend.db import ROLES, SessionLocal, User, init_db
from backend.security import hash_password


def _prompt_password() -> str:
    first = getpass.getpass("Password (min 8 characters): ")
    second = getpass.getpass("Repeat password: ")
    if first != second:
        raise SystemExit("Passwords do not match.")
    if len(first) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    return first


def create_user(email: str, role: str, full_name: str, password: str | None) -> None:
    if role not in ROLES:
        raise SystemExit(f"Role must be one of: {', '.join(ROLES)}")
    email = email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)) is not None:
            raise SystemExit(f"A user with email {email} already exists.")
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            password_hash=hash_password(password or _prompt_password()),
        )
        db.add(user)
        db.commit()
        print(f"Created {role} user {email} (id={user.id}).")


def seed_demo(confirm: bool) -> None:
    if not confirm:
        raise SystemExit("Refusing to seed demo data without --confirm.")
    from backend.db import Lead

    rows = [
        {
            "company_name": "Northwind Logistics",
            "industry": "Logistics",
            "contact_name": "Ada Fernandes",
            "email": "ada@northwind.example",
            "stage": "discovery",
            "company_size": "201-500",
            "annual_revenue": "$50M-$100M",
            "funding_stage": "Series B",
            "tech_stack": "Salesforce, Snowflake, Looker",
            "prospect_role": "VP Revenue Operations",
            "company_description": "Regional freight operator modernising dispatch and revenue reporting across 14 depots.",
            "explicit_needs": "Reduce manual revenue reporting and improve forecast accuracy before the next board cycle.",
            "engagement_history": "Attended webinar; replied to the follow-up and asked for a discovery call.",
            "response_behavior": "Positive and responsive",
            "user_research": "Hiring a RevOps analyst; current reporting is spreadsheet-heavy.",
            "pain_points": "manual reporting, forecast accuracy",
        },
        {
            "company_name": "Contoso Manufacturing",
            "industry": "Manufacturing",
            "contact_name": "Lee Chan",
            "email": "lee@contoso.example",
            "stage": "qualified",
            "company_size": "501-1000",
            "annual_revenue": "$100M-$250M",
            "funding_stage": "Private",
            "tech_stack": "SAP, Power BI",
            "prospect_role": "Director of Sales Operations",
            "company_description": "Industrial components manufacturer expanding its aftermarket service business.",
            "explicit_needs": "Connect service usage data to renewal risk and prioritise account coverage.",
            "engagement_history": "Discovery meeting completed; security review requested.",
            "response_behavior": "Interested, asked detailed integration questions",
            "user_research": "Two business units evaluate tools separately; procurement is centralised.",
            "pain_points": "renewal risk, account coverage",
        },
        {
            "company_name": "Fabrikam Retail",
            "industry": "Retail",
            "contact_name": "Priya Nair",
            "email": "priya@fabrikam.example",
            "stage": "prospecting",
            "company_size": "51-200",
            "annual_revenue": "$10M-$25M",
            "funding_stage": "Bootstrapped",
            "tech_stack": "Shopify, Klaviyo",
            "prospect_role": "Head of E-commerce",
            "company_description": "Direct-to-consumer retailer growing through seasonal campaigns.",
            "explicit_needs": "Improve campaign segmentation without adding headcount.",
            "engagement_history": "Downloaded the planning guide; no reply yet.",
            "response_behavior": "Opened emails, no response",
            "user_research": "Peak-season planning starts in six weeks.",
            "pain_points": "segmentation, campaign workload",
        },
        {
            "company_name": "InnovateAI Labs",
            "industry": "Artificial Intelligence",
            "contact_name": "Mark Chen",
            "email": "mark@innovateai.example",
            "stage": "proposal",
            "company_size": "11-50",
            "annual_revenue": "$5M-$10M",
            "funding_stage": "Series A",
            "tech_stack": "AWS, Python, dbt",
            "prospect_role": "Chief Revenue Officer",
            "company_description": "Applied-AI startup selling workflow automation to mid-market operations teams.",
            "explicit_needs": "Increase qualified pipeline while keeping sales headcount flat.",
            "engagement_history": "Two demos delivered; proposal sent; pricing review in progress.",
            "response_behavior": "Positive, requested a revised proposal",
            "user_research": "Board expects net-new ARR growth next quarter.",
            "pain_points": "pipeline quality, sales capacity",
        },
        {
            "company_name": "Bluebird Health",
            "industry": "Healthcare AI",
            "contact_name": "Dr. Sofia Alvarez",
            "email": "sofia@bluebird.example",
            "stage": "negotiation",
            "company_size": "201-500",
            "annual_revenue": "$25M-$50M",
            "funding_stage": "Series C",
            "tech_stack": "Epic, Azure, Power BI",
            "prospect_role": "Chief Operating Officer",
            "company_description": "Clinical operations platform serving outpatient networks with strict privacy requirements.",
            "explicit_needs": "Shorten the patient-intake cycle and standardise reporting across clinics.",
            "engagement_history": "Security and legal review completed; commercial terms under negotiation.",
            "response_behavior": "Positive, legal approved",
            "user_research": "Rollout begins in the next fiscal quarter; privacy is the key objection.",
            "pain_points": "intake cycle time, reporting consistency",
        },
        {
            "company_name": "Vanguard Fintech",
            "industry": "Fintech",
            "contact_name": "Noah Williams",
            "email": "noah@vanguard.example",
            "stage": "converted",
            "company_size": "501-1000",
            "annual_revenue": "$250M+",
            "funding_stage": "Series D",
            "tech_stack": "GCP, Kafka, Tableau",
            "prospect_role": "VP Sales",
            "company_description": "Payments platform scaling a partner-led sales motion.",
            "explicit_needs": "Give partner managers a consistent view of lead quality and next actions.",
            "engagement_history": "Closed-won pilot; expansion discussion scheduled.",
            "response_behavior": "Positive, renewed",
            "user_research": "Expansion depends on measurable partner-sourced pipeline.",
            "pain_points": "partner visibility, next-best action",
        },
    ]
    with SessionLocal() as db:
        created = 0
        for row in rows:
            email = row["email"]
            if db.scalar(select(Lead).where(Lead.email_key == email)) is not None:
                continue
            db.add(
                Lead(
                    company_name=row["company_name"],
                    industry=row["industry"],
                    contact_name=row["contact_name"],
                    email=email,
                    email_key=email,
                    lifecycle_stage=row["stage"],
                    company_size=row["company_size"],
                    annual_revenue=row["annual_revenue"],
                    funding_stage=row["funding_stage"],
                    tech_stack=row["tech_stack"],
                    prospect_role=row["prospect_role"],
                    company_description=row["company_description"],
                    explicit_needs=row["explicit_needs"],
                    engagement_history=row["engagement_history"],
                    response_behavior=row["response_behavior"],
                    user_research=row["user_research"],
                    pain_points=row["pain_points"],
                    lead_source="Labelled demo data",
                )
            )
            created += 1
        db.commit()
        print(f"Seeded {created} clearly-labelled demo lead(s).")
        print("These are fictional records for a local demonstration, not customer data.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="backend.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    user_cmd = sub.add_parser("create-user", help="Create a user account")
    user_cmd.add_argument("--email", required=True)
    user_cmd.add_argument("--role", default="rep", choices=ROLES)
    user_cmd.add_argument("--full-name", default="")
    user_cmd.add_argument(
        "--password",
        default=None,
        help="Prefer the interactive prompt; passing a password on the command line "
        "leaves it in your shell history.",
    )

    sub.add_parser("init-db", help="Create tables directly from the models (development only)")

    seed_cmd = sub.add_parser("seed-demo", help="Insert clearly-labelled demo leads")
    seed_cmd.add_argument("--confirm", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "create-user":
        create_user(args.email, args.role, args.full_name, args.password)
    elif args.command == "init-db":
        init_db()
        print("Schema created from SQLAlchemy metadata.")
    elif args.command == "seed-demo":
        seed_demo(args.confirm)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
