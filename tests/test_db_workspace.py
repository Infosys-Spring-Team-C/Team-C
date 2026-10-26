"""Guards that the database workspace cannot drift from the canonical ORM.

``salesgenie-db-workspace/`` ships a generated ``init_schema.sql`` and a
generated ``er_diagram.html``. Both are derived from :mod:`backend.db`. These
tests fail if either artefact is stale, or if the rendered DDL loses a table or
a foreign-key rule.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = REPO_ROOT / "salesgenie-db-workspace"
SQL_PATH = WORKSPACE / "init_schema.sql"
ER_PATH = WORKSPACE / "er_diagram.html"
RENDERER = REPO_ROOT / "scripts" / "render_db_workspace.py"

EXPECTED_TABLES = {
    "users",
    "leads",
    "company_insights",
    "outreach_campaigns",
    "lead_scores",
    "sales_interactions",
    "crm_sync_logs",
    "sales_analytics",
}


def _renderer_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("JWT_SECRET", "unit-test-secret-value-0123456789")
    env.setdefault("AUTH_ENABLED", "true")
    return env


def test_generated_artefacts_match_the_orm():
    """`render_db_workspace.py --check` must report no diff."""
    result = subprocess.run(
        [sys.executable, str(RENDERER), "--check"],
        cwd=str(REPO_ROOT),
        env=_renderer_env(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "The database workspace is stale relative to backend/db.py.\n"
        "Run: python scripts/render_db_workspace.py\n\n"
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )


def test_init_schema_declares_the_eight_tables():
    sql = SQL_PATH.read_text(encoding="utf-8")
    declared = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", sql))
    assert declared == EXPECTED_TABLES


def test_init_schema_declares_six_foreign_keys_with_the_agreed_rules():
    sql = SQL_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"CREATE TABLE IF NOT EXISTS ", sql)[1:]

    rules: dict[tuple[str, str], str] = {}
    for block in blocks:
        child = re.match(r"(\w+)", block).group(1)
        for parent, on_delete in re.findall(
            r"REFERENCES (\w+) \(\w+\)(?: ON DELETE (\w+(?: \w+)?))?", block
        ):
            rules[(child, parent)] = (on_delete or "").upper()

    assert len(rules) == 6, rules
    assert rules[("leads", "users")] == "SET NULL"
    assert rules[("company_insights", "leads")] == "CASCADE"
    assert rules[("outreach_campaigns", "leads")] == "CASCADE"
    assert rules[("lead_scores", "leads")] == "CASCADE"
    assert rules[("sales_interactions", "leads")] == "CASCADE"
    assert rules[("crm_sync_logs", "leads")] == "SET NULL"


def test_init_schema_keeps_the_honesty_constraints():
    """A score probability and the open KPI metrics must be nullable.

    SRS D-09/D-10/D-13 are unresolved, so the database must be able to store
    "unknown" rather than a fabricated zero or a fake probability.
    """
    sql = SQL_PATH.read_text(encoding="utf-8")
    assert re.search(r"conversion_probability FLOAT,", sql)
    assert re.search(r"conversion_rate FLOAT,", sql)
    assert re.search(r"pipeline_value NUMERIC\(15, 2\),", sql)


def test_er_diagram_covers_every_table():
    html = ER_PATH.read_text(encoding="utf-8")
    assert "erDiagram" in html
    for table in EXPECTED_TABLES:
        assert table.upper() in html, f"{table} missing from the ER diagram"
    assert html.count("||--o{") == 6
