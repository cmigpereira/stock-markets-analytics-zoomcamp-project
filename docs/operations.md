# Reproduce and operate

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). Run commands from the repository root.

```bash
uv sync --frozen --extra dev --python 3.12
uv run etf-pressure run --mode download --start 2021-01-01 --end 2026-11-04
uv run streamlit run app.py
```

The end date is exclusive. Yahoo may return fewer sessions if the latest session has not closed. Initial download fetches about 1,465 public FINRA daily files for this window, filtering to the 40 configured ETFs before caching. Allow several minutes and internet access. Each filtered file retains its source URL, raw response SHA-256, retrieval timestamp, and source/selected row counts in a companion JSON file. These caches are under ignored `data/`.

The model fitting workload is 24 validation fits plus six final fits. Historical Yahoo prices use a ten-day overlap on incremental refresh to pick up recent revisions. Earlier adjusted history can still change; delete/move the price cache if you deliberately need a complete provider refresh, and preserve the old snapshot for comparison. FINRA cached sessions are immutable locally unless deliberately refreshed. Changing the universe requires a new data directory because FINRA caches are already ticker-filtered.

## Two modes

```bash
# No data requests: recompute features, models, simulations, and reports from local input.
uv run etf-pressure run --mode cached

# Incremental source refresh, then the same downstream workflow.
uv run etf-pressure run --mode download

# Package only combined inputs plus provenance, never executable models.
uv run etf-pressure snapshot
uv run etf-pressure restore /path/to/research-snapshot.zip
uv run etf-pressure run --mode cached
```

Exchange calendars exclude holidays and exceptional closures. Missing source sessions are recorded in `data/manifest.json`; FINRA coverage below 95% fails the run. Individual missing observations remain missing and are excluded by the rolling-feature requirements. A download failure does not create artificial zero activity. Retry to recover unavailable uncached files. Do not rename a synthetic demonstration dataset to look like downloaded history.

## Generated files

- `data/combined.parquet`: unique ETF-day source table, before feature warm-up.
- `data/features.parquet`: unified modeled table with features and forward labels.
- `data/manifest.json`: coverage, window, universe, and retrieval metadata.
- `artifacts/models.json`: every validation choice and test metric.
- `artifacts/summary.json`: input hash, row counts, paired-return uncertainty.
- `artifacts/curves.parquet`, `trades.csv`, `performance.csv`: exact accounting evidence.
- `artifacts/vector.json`: vectorized event-return screen, not a portfolio CAGR.
- `artifacts/cost_sensitivity.csv`, `calibration.csv`, `correlations.csv`, `by_ticker.csv`, `by_asset_class.csv`, `worst_predictions.csv`: diagnostic evidence.
- `artifacts/*.joblib`: local trained models. Never load serialized models from untrusted sources.

The Streamlit app loads presentation reports, not joblib files. It keys its cache on the source location and latest report-file modification time. Complete local outputs take precedence; a clean checkout uses the committed reports/dashboard.json without network requests. Downloading sources directly is the public reproduction route. A private snapshot is optional and subject to source terms. There is no preconfigured external snapshot link or paid storage dependency.

## Automation

`.github/workflows/ci.yml` runs lint and critical tests on pushes/PRs. `research.yml` supports manual runs and 02:30 UTC Tuesday–Saturday refreshes, after Monday–Friday US sessions. GitHub schedules are best effort, not guaranteed pre-open execution. A fresh workflow restores the most recent data cache, downloads missing sessions, writes reports, saves a new cache, and uploads only the derived dashboard report as a 30-day artifact; raw snapshots and model binaries are not published. GitHub cache eviction can force a full rebuild; it is not permanent storage. Review Actions quotas before enabling schedules in private repositories. No generated datasets are pushed to Git.

For a local scheduler, use absolute paths and the virtual environment installed above:

```cron
30 2 * * 2-6 cd /absolute/path/to/project && .venv/bin/etf-pressure run --mode download >> artifacts/refresh.log 2>&1
```

Create `artifacts/` first. Cron runs in the host timezone; choose UTC explicitly on the host or translate the schedule. This example does not install a cron job automatically.

## Docker and optional hosting

```bash
docker build -t etf-pressure-lab .
docker run --rm -p 8501:8501 -v "$PWD/artifacts:/app/artifacts:ro" etf-pressure-lab
```

The image includes the code, environment, and derived published report, so it can launch without a local artifacts mount. The example mount overrides that report with complete local outputs. Historical source data remains excluded. The Dockerfile is provided; consult the verification report for whether a local daemon was available to execute it.

For Streamlit Community Cloud, follow the [plug-and-play deployment guide](deployment.md): select the repository, `app.py`, and Python 3.12; leave secrets empty. The committed derived dashboard report makes the app usable immediately. No data download, model training, or storage integration is needed on the hosting server. To update the published results, run `uv run etf-pressure publish-report` after a completed research run, then review and commit the report. The app clearly identifies the published observation date and does not claim a live feed.

## Checks

```bash
uv run ruff check src tests scripts app.py
uv run pytest -q
uv run python scripts/capture_app.py
```

The screenshot script needs a locally running app and Playwright Chromium (`uv run playwright install chromium`). It checks all dashboard views before saving actual screenshots. The notebook is an executable interface to the same modules, with cached inputs by default; edit `MODE` to download.
