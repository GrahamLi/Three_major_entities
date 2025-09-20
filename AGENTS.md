# Repository Guidelines

## Project Structure & Module Organization
- Root: `twse_scraper.py` (main scraper CLI) and `stock_list.csv` (input list: columns `stock_code`, `stock_name`, `上市上櫃` with values `上市` or `上櫃`).
- Docs: `ReadMe.md` (user guide), `PRD.md` (product notes).
- Data output: `data/twse_raw/<stock_id>/YYYY-MM-DD.csv` and `data/twse_raw/<stock_id>/<stock_id>.csv` (accumulation); mirrored under `data/tpex_raw/` for TPEx.

## Build, Test, and Development Commands
- Install deps: `pip install pandas requests` (no requirements file yet).
- Run daily scrape: `python twse_scraper.py` (defaults to 1 day).
- Backfill N days: `python twse_scraper.py --days 60`.
- Optional lint/format (if installed): `ruff check .`, `black .`.

## Coding Style & Naming Conventions
- Python 3.8+; follow PEP 8 with 4‑space indentation and 88‑char lines.
- Naming: `snake_case` for functions/vars, `UPPER_CASE` for constants (e.g., `HEADERS`, `ROOT_DIR`).
- Type hints: prefer explicit types for public functions; return `pd.DataFrame` for parsers.
- Logging: use `logging` (INFO by default). Avoid `print` in library code.

## Testing Guidelines
- No formal tests yet. Prefer `pytest` with files under `tests/` named `test_*.py`.
- Focus tests on pure functions: `decode_content`, `parse_twse_csv`, `parse_tpex_csv`, `merge_dataframes` using small CSV fixtures in `tests/fixtures/`.
- Example: `pytest -q` to run tests; `pytest -k parse_twse_csv` to target a module.

## Commit & Pull Request Guidelines
- Commits: use concise, imperative messages. Conventional Commits preferred: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`.
- Scope commits narrowly (parser, IO, CLI). Include rationale when touching data schema or file layout.
- PRs: add a clear description, steps to reproduce/verify (commands and expected files), linked issues, and sample outputs (paths under `data/...`). Screenshots optional.

## Security & Configuration Tips
- SSL verification is disabled for data fetches to accommodate some endpoints. Keep this code path and headers intact; do not store secrets. Be mindful of site rate limits (there is a small sleep between requests).
- CSV encoding: outputs use `utf-8-sig`. Preserve this when writing/reading.
- Windows-friendly paths are used (`pathlib`). Keep new paths relative to repo root.

## Architecture Overview
- Pipeline: CSV fetch (requests) → robust decode → parser per market/source → merge per day → write per‑stock daily file → update per‑stock accumulation.
- Concurrency: uses `ThreadPoolExecutor` for per‑day processing; avoid blocking calls in parsing logic.
