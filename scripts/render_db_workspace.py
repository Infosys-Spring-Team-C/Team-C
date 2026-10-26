"""Render the database-workspace artefacts from the canonical ORM.

The canonical schema lives in :mod:`backend.db`. The database workspace
(``salesgenie-db-workspace/``) must never carry a second, hand-maintained copy of
it, because two definitions of one schema drift apart. This script derives both
artefacts that the workspace ships:

* ``init_schema.sql``   - portable PostgreSQL DDL for a fresh database
* ``er_diagram.html``   - the entity-relationship diagram

Usage
-----
Regenerate both files::

    python scripts/render_db_workspace.py

Verify that the committed files still match the ORM (used by the test suite and
safe to run in CI)::

    python scripts/render_db_workspace.py --check

``--check`` exits ``1`` and prints the first differing lines when a file is
stale, so a schema change cannot silently leave the workspace behind.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from backend.db import Base  # noqa: E402

WORKSPACE = REPO_ROOT / "salesgenie-db-workspace"
SQL_PATH = WORKSPACE / "init_schema.sql"
ER_PATH = WORKSPACE / "er_diagram.html"

SQL_HEADER = """\
-- ============================================================================
-- SalesGenie AI - PostgreSQL schema baseline (canonical, eight tables)
--
-- GENERATED FILE - do not edit by hand.
-- Source of truth : backend/db.py (SQLAlchemy models)
-- Regenerate      : python scripts/render_db_workspace.py
-- Verify          : python scripts/render_db_workspace.py --check
--
-- The migration that builds the same schema in an existing database is
-- alembic/versions/0001_canonical_schema.py. This file is the portable
-- equivalent for a brand-new database (for example the Docker entrypoint).
-- ============================================================================

"""

ER_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SalesGenie AI - Entity-Relationship (ER) Diagram</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: #f8fafc;
      color: #1e293b;
      margin: 0;
      padding: 30px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .header {{ text-align: center; margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px 0; color: #0f172a; font-size: 26px; }}
    .subtitle {{ color: #64748b; font-size: 15px; margin-bottom: 4px; }}
    .badge {{
      display: inline-block;
      background: #e0e7ff;
      color: #4338ca;
      font-size: 13px;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 9999px;
    }}
    .card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
      max-width: 1200px;
      width: 100%;
      overflow-x: auto;
    }}
    .footer {{ margin-top: 20px; color: #64748b; font-size: 13px; text-align: center; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>SalesGenie AI - Entity-Relationship Diagram</h1>
    <div class="subtitle">Canonical eight-table schema used by the FastAPI backend</div>
    <div class="badge">Generated from backend/db.py</div>
  </div>

  <div class="card">
    <div class="mermaid">
{diagram}
    </div>
  </div>

  <div class="footer">
    GENERATED FILE - regenerate with <code>python scripts/render_db_workspace.py</code>.
    Authoritative source: <code>backend/db.py</code>.
  </div>

  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'default',
      er: {{ useMaxWidth: false }}
    }});
  </script>
</body>
</html>
"""

_ER_TYPES = {
    "INTEGER": "int",
    "BIGINT": "int",
    "SMALLINT": "int",
    "VARCHAR": "string",
    "CHAR": "string",
    "TEXT": "text",
    "BOOLEAN": "bool",
    "FLOAT": "float",
    "NUMERIC": "decimal",
    "DECIMAL": "decimal",
    "JSON": "json",
    "JSONB": "json",
    "DATETIME": "timestamp",
    "TIMESTAMP": "timestamp",
    "DATE": "date",
    "TIME": "time",
}


def render_sql() -> str:
    """Return the complete PostgreSQL DDL for the canonical schema."""
    dialect = postgresql.dialect()
    parts: list[str] = [SQL_HEADER]

    for table in Base.metadata.sorted_tables:
        parts.append(
            str(CreateTable(table, if_not_exists=True).compile(dialect=dialect)).strip() + ";\n"
        )
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            try:
                statement = CreateIndex(index, if_not_exists=True).compile(dialect=dialect)
            except TypeError:  # pragma: no cover - older SQLAlchemy
                statement = CreateIndex(index).compile(dialect=dialect)
            parts.append(str(statement).strip() + ";\n")
        parts.append("\n")

    return "".join(parts).rstrip() + "\n"


def _er_type(column) -> str:
    name = column.type.__class__.__name__.upper()
    return _ER_TYPES.get(name, name.lower())


def render_er() -> str:
    """Return the complete HTML ER diagram for the canonical schema."""
    tables = list(Base.metadata.sorted_tables)
    lines: list[str] = ["erDiagram"]

    for table in tables:
        lines.append(f"    {table.name.upper()} {{")
        for column in table.columns:
            flags: list[str] = []
            if column.primary_key:
                flags.append("PK")
            if column.unique:
                flags.append("UK")
            if column.foreign_keys:
                flags.append("FK")
            suffix = (" " + " ".join(flags)) if flags else ""
            lines.append(f"        {_er_type(column)} {column.name}{suffix}")
        lines.append("    }")

    for table in tables:
        for fk in sorted(table.foreign_keys, key=lambda item: item.parent.name):
            parent = fk.column.table.name.upper()
            child = table.name.upper()
            rule = (fk.ondelete or "").upper()
            label = {"CASCADE": "cascades", "SET NULL": "sets null"}.get(rule, "references")
            lines.append(f"    {parent} ||--o{{ {child} : {label}")

    return ER_TEMPLATE.format(diagram="\n".join("    " + line if i else line
                                                for i, line in enumerate(lines)))


def _report(path: Path, expected: str) -> bool:
    actual = path.read_text(encoding="utf-8") if path.exists() else ""
    if actual == expected:
        print(f"OK    {path.relative_to(REPO_ROOT)}")
        return True
    diff = list(
        difflib.unified_diff(
            actual.splitlines(),
            expected.splitlines(),
            fromfile=f"{path.name} (committed)",
            tofile=f"{path.name} (from backend/db.py)",
            lineterm="",
        )
    )
    print(f"STALE {path.relative_to(REPO_ROOT)}")
    for line in diff[:40]:
        print("      " + line)
    if len(diff) > 40:
        print(f"      ... {len(diff) - 40} more diff lines")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artefacts match backend/db.py without writing",
    )
    args = parser.parse_args(argv)

    sql = render_sql()
    er = render_er()

    if args.check:
        ok = _report(SQL_PATH, sql) & _report(ER_PATH, er)
        return 0 if ok else 1

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    SQL_PATH.write_text(sql, encoding="utf-8")
    ER_PATH.write_text(er, encoding="utf-8")
    print(f"Wrote {SQL_PATH.relative_to(REPO_ROOT)}")
    print(f"Wrote {ER_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
