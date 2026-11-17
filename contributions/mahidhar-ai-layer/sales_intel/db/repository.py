"""Persistence for the AI/ML layer.

The AI services are pure functions; persistence is injected. This gives us:
  * `InMemoryRepository`  — default for tests, CI and offline demos;
  * `PostgresRepository`  — real DealFlow tables (Lead_Scores, Sales_Interactions,
                            Action_Items, NBA_Recommendations) via psycopg.

Set `SI_DATABASE_URL` (e.g. postgresql://user:pass@localhost:5432/dealflow) to
switch to Postgres. If the driver or DB is unavailable the app degrades to
in-memory rather than failing the request.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Protocol

from sales_intel.schemas import ActionItem, ConversationSummary, LeadScore, NextBestAction

log = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS lead_scores (
    id                BIGSERIAL PRIMARY KEY,
    lead_id           TEXT        NOT NULL,
    score             NUMERIC(5,2) NOT NULL,
    band              TEXT        NOT NULL,
    conversion_probability NUMERIC(6,5) NOT NULL,
    subscores         JSONB       NOT NULL,
    drivers           JSONB       NOT NULL,
    model_version     TEXT        NOT NULL,
    scored_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lead_scores_lead ON lead_scores (lead_id, scored_at DESC);

CREATE TABLE IF NOT EXISTS sales_interactions (
    interaction_id    TEXT PRIMARY KEY,
    lead_id           TEXT,
    interaction_type  TEXT        NOT NULL DEFAULT 'meeting',
    summary           TEXT        NOT NULL,
    key_points        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    decisions         JSONB       NOT NULL DEFAULT '[]'::jsonb,
    objections        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    competitors_mentioned JSONB   NOT NULL DEFAULT '[]'::jsonb,
    next_step         TEXT,
    sentiment         TEXT,
    talk_ratio_internal NUMERIC(5,4),
    confidence        NUMERIC(5,4),
    engine            TEXT,
    model             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_interactions_lead ON sales_interactions (lead_id, created_at DESC);

CREATE TABLE IF NOT EXISTS action_items (
    id                BIGSERIAL PRIMARY KEY,
    interaction_id    TEXT        NOT NULL REFERENCES sales_interactions(interaction_id) ON DELETE CASCADE,
    lead_id           TEXT,
    task              TEXT        NOT NULL,
    owner             TEXT,
    owner_side        TEXT,
    due_date          DATE,
    due_hint          TEXT,
    priority          TEXT,
    source_quote      TEXT,
    status            TEXT        NOT NULL DEFAULT 'open',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_action_items_open ON action_items (status, due_date);

CREATE TABLE IF NOT EXISTS nba_recommendations (
    id                BIGSERIAL PRIMARY KEY,
    lead_id           TEXT        NOT NULL,
    priority          TEXT        NOT NULL,
    priority_score    NUMERIC(5,2) NOT NULL,
    recommended_channel TEXT      NOT NULL,
    next_touch_date   DATE        NOT NULL,
    cadence           JSONB       NOT NULL DEFAULT '[]'::jsonb,
    channel_mix       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    content_strategy  JSONB       NOT NULL DEFAULT '{}'::jsonb,
    rationale         JSONB       NOT NULL DEFAULT '[]'::jsonb,
    risk_flags        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    generated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_nba_lead ON nba_recommendations (lead_id, generated_at DESC);
"""


class Repository(Protocol):
    def save_score(self, score: LeadScore) -> None: ...
    def save_nba(self, nba: NextBestAction) -> None: ...
    def save_summary(self, summary: ConversationSummary) -> int: ...
    def recent_activity(self, limit: int = 20) -> list[dict[str, Any]]: ...
    def open_action_items(self, owner: str | None = None) -> list[dict[str, Any]]: ...


# ---------------------------------------------------------------------------
class InMemoryRepository:
    def __init__(self) -> None:
        self.scores: list[LeadScore] = []
        self.nbas: list[NextBestAction] = []
        self.summaries: list[ConversationSummary] = []

    def save_score(self, score: LeadScore) -> None:
        self.scores.append(score)

    def save_nba(self, nba: NextBestAction) -> None:
        self.nbas.append(nba)

    def save_summary(self, summary: ConversationSummary) -> int:
        self.summaries.append(summary)
        return len(summary.action_items)

    def recent_activity(self, limit: int = 20) -> list[dict[str, Any]]:
        feed: list[dict[str, Any]] = []
        for s in self.summaries:
            feed.append({
                "type": "meeting_summary",
                "lead_id": s.lead_id,
                "reference": s.interaction_id,
                "headline": s.summary[:120],
                "at": s.created_at.isoformat(),
                "open_actions": len(s.action_items),
            })
        for n in self.nbas:
            feed.append({
                "type": "nba_recommendation",
                "lead_id": n.lead_id,
                "reference": n.lead_id,
                "headline": f"{n.priority} · {n.recommended_channel} on {n.next_touch_date}",
                "at": n.generated_at.isoformat(),
                "open_actions": 0,
            })
        for s in self.scores:
            feed.append({
                "type": "lead_score",
                "lead_id": s.lead_id,
                "reference": s.lead_id,
                "headline": f"{s.score:.1f} ({s.band}) · P(win)={s.conversion_probability:.0%}",
                "at": s.scored_at.isoformat(),
                "open_actions": 0,
            })
        return sorted(feed, key=lambda r: r["at"], reverse=True)[:limit]

    def open_action_items(self, owner: str | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for s in self.summaries:
            for a in s.action_items:
                if owner and a.owner.lower() != owner.lower():
                    continue
                rows.append({"interaction_id": s.interaction_id, "status": "open", **a.model_dump(mode="json")})
        return sorted(rows, key=lambda r: (r.get("due_date") or "9999", r["task"]))


# ---------------------------------------------------------------------------
class PostgresRepository:
    def __init__(self, dsn: str) -> None:
        import psycopg  # imported lazily so the app runs without the driver

        self._psycopg = psycopg
        self.dsn = dsn
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
            conn.commit()

    def _conn(self):
        return self._psycopg.connect(self.dsn, autocommit=False)

    def save_score(self, score: LeadScore) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO lead_scores
                   (lead_id, score, band, conversion_probability, subscores, drivers, model_version, scored_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (score.lead_id, score.score, score.band, score.conversion_probability,
                 json.dumps(score.subscores), json.dumps(score.drivers),
                 score.model_version, score.scored_at),
            )
            conn.commit()

    def save_nba(self, nba: NextBestAction) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO nba_recommendations
                   (lead_id, priority, priority_score, recommended_channel, next_touch_date,
                    cadence, channel_mix, content_strategy, rationale, risk_flags, generated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (nba.lead_id, nba.priority, nba.priority_score, nba.recommended_channel,
                 nba.next_touch_date,
                 json.dumps([t.model_dump(mode="json") for t in nba.cadence]),
                 json.dumps([c.model_dump() for c in nba.channel_mix]),
                 json.dumps(nba.content.model_dump()),
                 json.dumps(nba.rationale), json.dumps(nba.risk_flags), nba.generated_at),
            )
            conn.commit()

    def save_summary(self, summary: ConversationSummary) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO sales_interactions
                   (interaction_id, lead_id, interaction_type, summary, key_points, decisions,
                    objections, competitors_mentioned, next_step, sentiment,
                    talk_ratio_internal, confidence, engine, model, created_at)
                   VALUES (%s,%s,'meeting',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (interaction_id) DO UPDATE SET
                     summary = EXCLUDED.summary,
                     key_points = EXCLUDED.key_points,
                     confidence = EXCLUDED.confidence,
                     model = EXCLUDED.model""",
                (summary.interaction_id, summary.lead_id, summary.summary,
                 json.dumps([p.model_dump() for p in summary.key_discussion_points]),
                 json.dumps(summary.decisions), json.dumps(summary.objections),
                 json.dumps(summary.competitors_mentioned), summary.next_step,
                 summary.overall_sentiment, summary.talk_ratio_internal,
                 summary.confidence, summary.engine, summary.model, summary.created_at),
            )
            cur.execute("DELETE FROM action_items WHERE interaction_id = %s", (summary.interaction_id,))
            for a in summary.action_items:
                cur.execute(
                    """INSERT INTO action_items
                       (interaction_id, lead_id, task, owner, owner_side, due_date, due_hint,
                        priority, source_quote)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (summary.interaction_id, summary.lead_id, a.task, a.owner, a.owner_side,
                     a.due_date, a.due_hint, a.priority, a.source_quote),
                )
            conn.commit()
        return len(summary.action_items)

    def recent_activity(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT interaction_id, lead_id, summary, created_at,
                          (SELECT count(*) FROM action_items ai
                            WHERE ai.interaction_id = si.interaction_id AND ai.status = 'open')
                   FROM sales_interactions si
                   ORDER BY created_at DESC LIMIT %s""",
                (limit,),
            )
            return [
                {"type": "meeting_summary", "reference": r[0], "lead_id": r[1],
                 "headline": r[2][:120], "at": r[3].isoformat(), "open_actions": r[4]}
                for r in cur.fetchall()
            ]

    def open_action_items(self, owner: str | None = None) -> list[dict[str, Any]]:
        q = """SELECT interaction_id, task, owner, owner_side, due_date, priority, source_quote
               FROM action_items WHERE status = 'open'"""
        params: tuple[Any, ...] = ()
        if owner:
            q += " AND lower(owner) = lower(%s)"
            params = (owner,)
        q += " ORDER BY due_date NULLS LAST, priority"
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(q, params)
            return [
                {"interaction_id": r[0], "task": r[1], "owner": r[2], "owner_side": r[3],
                 "due_date": r[4].isoformat() if r[4] else None, "priority": r[5],
                 "source_quote": r[6], "status": "open"}
                for r in cur.fetchall()
            ]


# ---------------------------------------------------------------------------
_repo: Repository | None = None


def get_repository() -> Repository:
    global _repo
    if _repo is not None:
        return _repo
    dsn = os.getenv("SI_DATABASE_URL", "")
    if dsn:
        try:
            _repo = PostgresRepository(dsn)
            log.info("AI/ML persistence: PostgreSQL")
            return _repo
        except Exception as exc:  # noqa: BLE001
            log.warning("Postgres unavailable (%s) — using in-memory store", exc)
    _repo = InMemoryRepository()
    log.info("AI/ML persistence: in-memory")
    return _repo


def reset_repository() -> None:
    """Test helper."""
    global _repo
    _repo = None
