# Git Report

**Repository:** `https://github.com/Infosys-Spring-Team-C/Team-C`
**Branch:** `feature/backend-integration`
**Base:** `main` at `f3724a2` (`chore: retain only files added beyond source ZIP`)
**Implementation commit:** `9ddc617799c979d4418f61e1c3ac4f1e3b3a80af`
**Author:** `isharak7m <192635824+isharak7m@users.noreply.github.com>`
**Date:** 26 October 2026
**Push status:** **not pushed.** No GitHub credentials are configured on this machine
(`gh auth status` -> "You are not logged into any GitHub hosts"), so no push, no pull request and
no remote branch exist.

This report is committed as a separate commit immediately after `9ddc617`; `git log --oneline -2`
shows both.

---

## 1. Commit

```
9ddc617 feat: implement tested FastAPI backend and canonical schema
f3724a2 chore: retain only files added beyond source ZIP   (origin/main)
```

`git rev-list --left-right --count origin/main...HEAD` -> `0  1` (one commit ahead, nothing
behind). The branch is a normal fast-forward from `main`; no history was rewritten and no
force-push was used. The commit message was corrected once before any push (a UTF-8 BOM in the
subject line), which is why the hash is `9ddc617` rather than the initial `e338a96`.

```
54 files changed, 9627 insertions(+), 500 deletions(-)
```

### Added

| Area | Files |
|---|---|
| Application | `backend/config.py`, `backend/security.py`, `backend/schemas.py`, `backend/errors.py`, `backend/deps.py`, `backend/cli.py` |
| Routers | `backend/routers/{__init__,_helpers,auth,leads,intelligence,outreach,scoring,conversations,analytics}.py` |
| Services | `backend/services/{__init__,leads,csv_import,analytics}.py` |
| Intelligence | `backend/intelligence/{__init__,contract,heuristic,external}.py` |
| Migration | `alembic/versions/0001_canonical_schema.py` |
| Tests | `tests/{conftest,test_api_leads,test_api_auth,test_api_import,test_api_ai,test_intelligence,test_schema,test_postgres}.py` |
| Packaging | `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore`, `README.md` |
| Docs | `docs/{SRS,audit-report,database-review,ai-review,api-contract,frontend-integration,test-report,contributor-actions,milestone-readiness}.md` |

### Modified

| File | Change |
|---|---|
| `backend/api.py` | Replaced the module that imported nonexistent `ai.*`/`utils.*` with an application factory, health endpoint, CORS, error handlers and router wiring |
| `backend/db.py` | Rebuilt as the canonical eight-table model with indexes, cascade rules and lifecycle vocabulary |
| `alembic/env.py` | Reads `DATABASE_URL` from settings; no hard-coded credentials |
| `alembic.ini` | Points at the local `alembic/` directory; no database URL with a password |
| `Dockerfile` | Non-root user, pinned install, health check, uvicorn `CMD`, removed the unused 8501 exposure |
| `docker-compose.yml` | Two services (`db`, `api`), required secrets, health-gated startup, `127.0.0.1` port binding, removed the nonexistent `ui` service |

### Deleted

| File | Reason |
|---|---|
| `alembic/versions/0001_core_schema.py` | `Base.metadata.create_all()` stub, replaced by explicit DDL |
| `tests/test_backend_api.py` | Could not even be imported; superseded by the eight test modules |

---

## 2. Verification at commit time

Run in a clean virtual environment created only from `requirements-dev.txt`:

| Command | Result |
|---|---|
| `python -m pytest -q` (SQLite) | `101 passed, 6 skipped` |
| `TEST_DATABASE_URL=... python -m pytest -q` (SQLite + PostgreSQL 16.15) | `107 passed` |
| `python -m alembic upgrade head` on SQLite | 8 tables + `alembic_version`, 24 indexes |
| `python -m alembic upgrade head` on PostgreSQL | 8 tables + `alembic_version`, 32 indexes |
| `alembic downgrade base` | Verified inside `tests/test_schema.py` |
| `docker compose config --quiet` | exit 0 |

Not verified at commit time, and not claimed: Docker image build and container start (no daemon),
`SALES_GENIE_AI_BACKEND=external` (AI package not merged), real provider calls, the Streamlit
frontend. Full detail: [`test-report.md`](test-report.md).

---

## 3. Security check performed before committing

```
git ls-files -co --exclude-standard | Select-String "\.env$|\.db$|\.sqlite"   -> no matches
Get-ChildItem -Recurse | Select-String "sk-proj-|postgres_password|CHANGE_ME"
```

Every hit was either a documented placeholder in `.env.example` (`CHANGE_ME_*`), a compose
variable reference (`${POSTGRES_PASSWORD:?...}`), or a quoted finding inside
`docs/database-review.md` describing the default password in Sai's repository. No `.env`, no
database file, no API key and no token is committed. `JWT_SECRET` has no default value in code:
the application refuses to start when `AUTH_ENABLED=true` and the secret is unset.

---

## 4. How to push and open the pull request

These commands have **not** been executed. They require an authenticated GitHub session with
write access to `Infosys-Spring-Team-C/Team-C`.

```powershell
cd C:\projects\infosys\Team-C

gh auth login                     # authenticate as the branch author, not as anyone else
gh auth status                    # confirm the active account

git push -u origin feature/backend-integration
```

Then, either with `gh`:

```powershell
gh pr create `
  --base main `
  --head feature/backend-integration `
  --title "Backend, canonical schema and intelligence integration" `
  --body-file docs/pr-description.md
```

or through the web UI using the compare link GitHub prints after the push.

**Do not** push directly to `main`, force-push, or merge without review. If the team uses branch
protection, the PR is the only permitted path, which is the intent.

### Suggested review order

1. `README.md` - scope and status table.
2. `docs/milestone-readiness.md` - what is and is not demonstrable.
3. `backend/db.py` + `alembic/versions/0001_canonical_schema.py` - schema.
4. `backend/intelligence/contract.py` + `heuristic.py` + `external.py` - AI boundary.
5. `tests/` - behaviour is specified here.
6. `docs/api-contract.md` - frontend surface.

---

## 5. Follow-up branches (not created)

The remaining work belongs to other contributors and must arrive as their own PRs:

| Work | Owner | Blocking dependency |
|---|---|---|
| `ai/` package + four-dimension mapping + provider hardening | Mahidhar | none - can start now |
| Migration/CI/index improvements rebased on `0001_canonical_schema` | Sai | this PR merged |
| Streamlit frontend against `/api/v1` | Maheksaba | this PR merged |
| Docker build verification | Project lead | Docker daemon |
| CI workflow | Sai / project lead | agreed database service |

Nothing in this branch modifies `team_c_sai` or `team-c-mahi`. Both were cloned read-only outside
the project tree and reviewed in [`database-review.md`](database-review.md) and
[`ai-review.md`](ai-review.md).
