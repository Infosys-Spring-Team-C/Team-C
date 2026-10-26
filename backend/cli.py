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
        ("Northwind Logistics", "Logistics", "Ada Fernandes", "ada@northwind.example", "discovery"),
        ("Contoso Manufacturing", "Manufacturing", "Lee Chan", "lee@contoso.example", "qualified"),
        ("Fabrikam Retail", "Retail", "Priya Nair", "priya@fabrikam.example", "prospecting"),
    ]
    with SessionLocal() as db:
        created = 0
        for company, industry, contact, email, stage in rows:
            if db.scalar(select(Lead).where(Lead.email_key == email)) is not None:
                continue
            db.add(
                Lead(
                    company_name=company,
                    industry=industry,
                    contact_name=contact,
                    email=email,
                    email_key=email,
                    lifecycle_stage=stage,
                    company_description="Demo record seeded by backend.cli; not real customer data.",
                )
            )
            created += 1
        db.commit()
        print(f"Seeded {created} demo lead(s).")


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
