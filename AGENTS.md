# Repository Guidelines

## Project Structure & Module Organization

`app.py` is the Streamlit entry point and composes the dashboard UI. Keep domain logic in `src/`: API access lives in `cartola.py` and `history.py`, persistence in `store.py`, prediction logic in `features.py` and `model.py`, simulations in `simulate.py` and `copa.py`, and presentation helpers in `viz.py`. Operational utilities belong in `scripts/`, including scheduled and manual data refreshes. Runtime caches and JSON snapshots are written under `data/`; do not commit generated data or model artifacts unless a change explicitly requires them. Container configuration is defined by `Dockerfile` and `docker-compose.yml`.

## Build, Test, and Development Commands

- `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` creates the local environment.
- `.venv/bin/streamlit run app.py` starts the dashboard at `http://localhost:8501`.
- `.venv/bin/python scripts/update_data.py` refreshes Cartola data manually.
- `docker compose up -d --build` builds and starts the app, MongoDB, and updater.
- `docker compose logs -f updater` follows scheduled refresh activity.
- `docker compose down` stops containers while preserving the MongoDB volume.

There is currently no automated test command. Before submitting changes, at minimum import affected modules and exercise the relevant Streamlit flow.

## Coding Style & Naming Conventions

Use Python 3.12-compatible code, four-space indentation, and PEP 8 conventions. Name functions and variables with `snake_case`, classes with `PascalCase`, and constants with `UPPER_SNAKE_CASE`. Prefer small domain-focused functions, type hints for public interfaces, and concise docstrings where behavior is not obvious. Keep user-facing text in Portuguese to match the existing dashboard. No formatter or linter is configured, so keep imports grouped and avoid unrelated formatting churn.

## Testing Guidelines

When adding tests, place them in `tests/`, mirror source module names (for example, `tests/test_simulate.py`), and use `test_<behavior>` names. Favor deterministic unit tests for standings, feature generation, probabilities, and simulations; seed random inputs where applicable. Mock external HTTP and MongoDB access rather than depending on live services.

## Commit & Pull Request Guidelines

Follow the existing history: concise, imperative Portuguese subjects such as `Adiciona validação da rodada`. Keep each commit focused. Pull requests should explain the user-visible outcome, list validation performed, and link relevant issues. Include screenshots for dashboard or chart changes, and call out configuration, data-schema, or environment-variable changes explicitly.

## Security & Configuration

Configure `MONGO_URL`, `TZ`, `UPDATE_TIMES`, and `ENABLE_UPDATER` through the environment. Never commit credentials, production connection strings, or private datasets. Treat remote API responses as untrusted and preserve the existing offline/cache fallback behavior.
