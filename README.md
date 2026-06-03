# UpsellAgent — Org-Intelligence & ICP-Matching for Sales

Turn an existing customer into a map of **who to talk to next**. Give the tool a
**company**, the **contacts you already know**, and your **Ideal Customer Profile
(ICP)** — it gathers people and signals from available sources, reconstructs an
**org chart / relationship graph** ("who works with whom"), scores every contact
against your ICP, and hands your sales team a ranked, sourced list of upsell
opportunities.

> Status: **MVP scaffold** (Phase 0 + start of Phase 1 of the roadmap). Runs
> fully in **mock mode** with zero external API keys, so the whole flow —
> analyze → org chart → ranked contacts → CSV export — works out of the box.

## Architecture

```
React/TS frontend  ──REST──►  FastAPI backend
  Wizard                        API + ICP scoring engine
  Org-chart (React Flow)        LLM orchestration (Claude)
  Ranked contacts + export      Provenance / compliance layer
                                       │
              Connector layer ── pipeline (Arq/Redis) ── PostgreSQL
              (compliant + shadow)                        people / edges /
                                                          ICP / provenance
```

- **Connector layer** (`backend/app/connectors/`): every source — a compliant API
  or a shadow scraper — implements the same `SourceAdapter` contract, so sources
  are swappable and stackable. Ships with a deterministic `mock` adapter, a
  `serpapi_news` adapter (Google News), and an inert, gated `shadow_linkedin`
  fallback.
- **Pipeline** (`backend/app/pipeline/`): sources → entity resolution → graph →
  ICP scoring, with per-step progress on the job.
- **Graph builder** (`backend/app/graph/`): hierarchy inference + `works_with` /
  `co_mentioned` edges, each with a confidence and an evidence reference.
- **Scoring** (`backend/app/scoring/`): Anthropic Claude when `ANTHROPIC_API_KEY`
  is set, otherwise a transparent keyword/seniority heuristic.
- **Compliance** (`backend/app/compliance/`): provenance on every datapoint,
  GDPR suppression list, lawful-basis tagging.

## Data sources & compliance

Primary sources are **compliant** (licensed APIs + public data). A **hidden
shadow/fallback** mode (scraping) exists but is:

- **off by default** (`ENABLE_SHADOW_SOURCES=false`),
- additionally gated by a **per-request admin opt-in** (`allow_shadow`),
- **audit-logged** on every activation,
- and tagged `source_mode=shadow` so it is clearly marked in the UI and exports.

The shipped shadow adapter is an **inert stub** — wire it to a licensed provider
only where legally permitted. Scraping LinkedIn/Xing violates their ToS and
carries GDPR risk in the EU.

## Quick start

### With Docker (Postgres + Redis + API + worker + web)

```bash
cp .env.example .env        # works as-is in mock mode
docker compose up --build
# API   → http://localhost:8000  (/docs for OpenAPI)
# Web   → http://localhost:5173
```

### Backend only (SQLite, no infra)

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload     # uses SQLite by default
pytest                            # full suite incl. end-to-end mock flow
ruff check .
```

### Frontend only

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

## Configuration

See `.env.example`. Everything is optional — without keys the app uses mock data
and heuristic scoring. Set `ANTHROPIC_API_KEY`, `SERPAPI_API_KEY`, etc. to enable
real LLM scoring and live sources.

## Roadmap

- **Phase 0** ✅ Scaffold, DB schema, CI, health check, mock end-to-end.
- **Phase 1** (in progress) Real compliant connector (Apollo/PDL) + provenance.
- **Phase 2** Arq worker, entity resolution, graph + Claude scoring at scale.
- **Phase 3** Org-chart UX polish, WebSocket progress, filters.
- **Phase 4** Auth (JWT/OIDC), CRM export (HubSpot/Pipedrive).
- **Phase 5** Shadow fallback hardening, suppression/retention, GDPR docs.
