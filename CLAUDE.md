# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Remo no Brasileirão** is a Streamlit dashboard that tracks the Clube do Remo's performance in the Brazilian league (Série A) using data from the Cartola FC API (`https://api.cartola.globo.com`). The system combines real-time standings, player performance, and probabilistic forecasts:

- **Prediction models** — XGBoost, Poisson (static & temporal), and Ensemble all trained for match-outcome forecasting
- **Monte Carlo simulations** — thousands of season scenarios to project final standings and compute probabilities (title, G4 promotion, Z4 relegation)
- **Copa do Brasil** — separate simulation for the knockout tournament (Poisson per-leg, penalty shootout logic)
- **Scheduled updates** — data refreshed 2× daily (08:00 & 22:00 in America/Belem timezone) via the `updater` service

Storage is pluggable: MongoDB in Docker, or JSON files locally. The codebase prioritizes offline availability — if an update fails, the last valid snapshot remains accessible.

## Common Commands

### Local Development (without Docker)

```bash
# Setup
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run the dashboard
.venv/bin/streamlit run app.py
# Opens http://localhost:8501

# Refresh data manually (API fetch, model training, simulations)
.venv/bin/python scripts/update_data.py
```

### Docker (Recommended)

```bash
# Build and start app, MongoDB, and updater
docker compose up -d --build

# Follow updater logs (scheduled refreshes)
docker compose logs -f updater

# Inspect MongoDB snapshots
docker compose exec mongo mongosh remo --eval 'db.season_daily.find({}, {fetched_at: 1}).sort({_id: -1})'

# Stop (preserves MongoDB volume)
docker compose down
```

### Environment Variables

- `MONGO_URL` — MongoDB connection string (triggers MongoDB backend; omit for local JSON)
- `TZ` — timezone for scheduler (default: America/Belem)
- `UPDATE_TIMES` — cron-style times for auto-refresh (default: `8,22`)
- `ENABLE_UPDATER` — set to `1` to run the scheduler alongside the dashboard
- `SIMULATION_MODEL` — `ensemble` (default), `xgboost`, `poisson`, or `poisson_temporal`
- `SIMULATION_COUNT` — number of Monte Carlo runs (default: 20000)
- `BACKTEST_ROUNDS` — historical rounds for model evaluation (default: 6)

## Architecture

### Entrypoint & Navigation

- **`app.py`** — Streamlit entry point; defines page routes, loads shared data (season snapshot or projection), and sets page config.
- **`pages/`** — Individual pages (Streamlit routing). Each module handles its own UI and interacts with `src/` for data.
  - `remo.py` — Remo's position, form, and probabilities.
  - `classificacao.py` — Full table with recent form and team shields.
  - `simulacoes.py` — Distribution heatmaps and Monte Carlo results.
  - `modelo.py` — Model backtest (accuracy, log loss, RPS over past rounds).
  - `copa.py` — Copa do Brasil bracket and simulated knockout.
  - `elenco.py`, `partidas.py` — Player rosters and match statistics.
  - `proximos_jogos.py` — 1×2 probabilities for upcoming fixtures.
  - `admin.py` — Manual data refresh and system status.

### Core Data Pipeline (`src/`)

- **`cartola.py`** — Cartola FC API client. Fetches rounds, clubs, matches, player stats, and team lineups.
- **`history.py`** — Caches historical Brasileirão data (2012+, ~5,300 matches) from football-data.co.uk. Weighted by recency for training.
- **`store.py`** — Dual-backend persistence: MongoDB (Docker) or JSON files (`data/season.json`, `data/daily/`). Handles snapshots (`season`), daily rollups (`season_daily`), daily player stats (`atletas_daily`), per-match points (`pontuados`), and Copa simulations.
- **`standings.py`** — Calculates tables (points, wins, tiebreakers: goal diff, goals for) and computes rolling form metrics (points per game, recent goal averages by home/away).

### Prediction & Simulation (`src/`)

- **`features.py`** — Generates tabular match features: form indicators (PPG, recent scoring), Elo ratings (updated match-by-match), home/away splits. Merges current-season and historical data.
- **`model.py`** — Four model classes:
  - **XGBoost** — Poisson regression with historical + current-season training.
  - **Poisson** — Static mean goals (simple rolling averages).
  - **Poisson Temporal** — Exponentially-weighted recent performance.
  - **Ensemble** — Arithmetic mean of all three.
  
  All predict Poisson rate parameters (λ) for goals per team per match. Training takes <1 second.

- **`simulate.py`** — Vectorized Monte Carlo: samples outcomes from predicted Poisson rates for all remaining matches, recalculates standings, computes final-position probabilities and expected points.
- **`copa.py`** — Separate simulator for Copa do Brasil: Poisson legs (home & away), penalty shootout logic (50% for each club if tied), and phase-by-phase probability aggregation.

### Evaluation & Reporting

- **`evaluate.py`** — Walk-forward backtest: trains only on past rounds, evaluates on holdout rounds. Metrics: accuracy (1×2 classification), log loss (probability calibration), RPS (ranked probability score for points).
- **`projections.py`** — Offline snapshot generator: runs full pipeline (fetch, feature engineering, train all models, simulate 20k times) and writes pre-computed results to `data/projection.json` for public dashboard read-only access.
- **`dashboard.py`** — Shared UI helpers (metric cards, formatting utilities).
- **`page_runner.py`** — Common executor used by page routes to ensure consistent data loading and error handling.
- **`viz.py`** — Plotting palette and Streamlit-specific styling.

### Operational (`scripts/`)

- **`scheduler.py`** — Daemon that runs at configured times (08:00, 22:00) and invokes `update_data.py`.
- **`update_data.py`** — Fetches Cartola APIs, re-trains models, simulates season, saves snapshots to storage backend.
- **`start.sh`** — Entrypoint for Docker: starts scheduler (if `ENABLE_UPDATER=1`) and dashboard concurrently.

### Data Storage

- **`data/`** — JSON cache for offline mode.
  - `season.json` — current snapshot.
  - `daily/season-YYYY-MM-DD.json` — one per day.
  - `projection.json` — pre-computed public-dashboard read-only snapshot (published 2× daily).
  - `historical/` — cached matches from football-data.co.uk (2012+).
  - `atletas.json`, `pontuados/`, etc. — auxiliary player and match-level stats.

- **MongoDB** (when `MONGO_URL` is set) — collections `season`, `season_daily`, `atletas`, `atletas_daily`, `pontuados`, `copa`.

## Key Patterns & Constraints

### Dual-Backend Persistence

The codebase handles two environments: Docker (production, MongoDB) and direct Python (development, JSON). Always check `store.py` for the active backend. Functions like `load_or_refresh()` transparently pick the right storage layer based on `MONGO_URL`.

### Offline Availability

If an API call or model training fails, the app displays the last valid snapshot. This is a feature, not a bug. New pages should follow this pattern: load cached data and gracefully degrade if updates are unavailable.

### Data Freshness Guarantees

- **Docker**: `updater` runs on schedule; dashboard always reads the latest snapshot from MongoDB.
- **Local (JSON)**: Dashboard auto-refetches if local data is >24 hours old. Manual refresh via `scripts/update_data.py`.

### Type Hints & Documentation

Public-facing functions have type hints. Docstrings are minimal (one line) — code should be self-explanatory. Keep imports grouped (stdlib, third-party, local).

### Streaming Output

Streamlit pages use `st.write()`, `st.metric()`, `st.table()`, `st.plotly_chart()`, etc. for output. Avoid stateful side effects in page logic; rely on Streamlit's caching (`@st.cache_data`, `@st.cache_resource`) for expensive operations.

### Language & Naming

All user-facing text is in Portuguese to match the existing dashboard. Variables and functions use `snake_case`, classes use `PascalCase`, constants use `UPPER_SNAKE_CASE`.

## Testing & Validation

There is no automated test suite configured. Before submitting changes:

1. **Import the affected module** — ensure no syntax or import errors.
2. **Exercise the relevant flow** — run the dashboard locally and interact with the modified page or feature.
3. **For model/simulation changes** — manually validate backtest metrics or compare probability distributions before/after.

If adding tests, place them in `tests/`, mirror the source module structure (e.g., `tests/test_simulate.py`), and seed random inputs for determinism.

## Deployment

### Docker (Railway or Local)

The Dockerfile builds a single image for both app and updater. Set `ENABLE_UPDATER=1` to enable the scheduler; `ENABLE_UPDATER=0` (or omit) disables it.

**Railway environment variables** (example):

```
MONGO_URL=${{MongoDB.MONGO_URL}}
TZ=America/Belem
ENABLE_UPDATER=1
SIMULATION_MODEL=ensemble
SIMULATION_COUNT=20000
BACKTEST_ROUNDS=6
```

Pushes to `main` trigger automatic deploys. Use `railway up` to test without committing.

### Important Notes for Changes

- **Do not commit generated data** — `data/season.json`, `data/daily/`, model artifacts in `models/daily/` are ephemeral. Commit only source code and dependencies (`requirements.txt`).
- **Configuration via environment** — never hardcode API keys, connection strings, or sensitive data. Use environment variables.
- **API resilience** — treat remote API responses as untrusted; preserve fallback behavior for failed requests.
- **Timezone awareness** — scheduler and data timestamps must respect `TZ` environment variable. Use UTC internally; convert for display.

## Related Documentation

See `AGENTS.md` for detailed coding style, commit message conventions, and pull request guidelines.
