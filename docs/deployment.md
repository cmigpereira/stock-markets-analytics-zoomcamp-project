# Streamlit Community Cloud: connect and deploy

The app is ready for a clean GitHub checkout. No secrets, API credentials, uploaded datasets, external storage, startup commands, or initial model training are needed to display it.

## Deployment steps

1. Complete the agreed final commit and push this project to your GitHub repository.
2. Sign into [Streamlit Community Cloud](https://share.streamlit.io/) and connect GitHub if prompted.
3. Click **Create app**, choose deployment from an existing repository, and select your repository and the branch containing these files.
4. Set the main file path to **`app.py`**.
5. In **Advanced settings**, select **Python 3.12**. Leave secrets empty.
6. Click **Deploy**. Once dependencies are installed, the app displays the published research results immediately.

These steps follow Streamlit's [deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app). Community Cloud automatically detects the root `uv.lock` before `requirements.txt`; the lock and `pyproject.toml` install the environment. There are no native system-library requirements or `packages.txt`. See [dependency discovery](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

## What launches on a new server

`reports/dashboard.json` is a compact export of computed research evidence: portfolio curves, performance metrics, model evaluation, predictions for the report's latest observation date, diagnostic tables, and the simulated trade ledger. It excludes raw historical OHLCV, FINRA input files, the unified training table, and serialized model objects. Like the figures and tables in the research notebook, it documents the experiment rather than supplying source datasets.

On a clean server, the app reads this file directly and labels it **Published research snapshot**. It makes no market-data requests and does not train models on the free hosting server. Sleep, reboot, and redeployment can reload the same committed report. Local filesystem persistence is unnecessary. The shown observation dates are authoritative; the published snapshot is not a live feed.

When a full set of local `artifacts/` exists, the same application uses those outputs instead. Incomplete local outputs fall back to the published report. File paths resolve relative to the application, not the shell's working directory.

## Updating the displayed research

To publish a newly computed report after reviewing its results:

```bash
uv run etf-pressure run --mode download
uv run etf-pressure publish-report
```

Review `reports/dashboard.json` and any changed documentation before your next commit/push. Streamlit follows the selected branch; it will then load the revised report. Regeneration is an explicit research/publication step, not a web request or an automatic Git commit.

The scheduled GitHub Actions workflow also exports `dashboard.json` inside its downloadable artifact. You can review that report and replace `reports/dashboard.json` with it before committing. GitHub artifacts are not required for hosting and no GitHub token is needed by the app.

## Verification boundary

The clean-checkout test copies only repository application files, source modules, configuration, and the published report into a temporary directory, with no `data/` or `artifacts/`. It disables socket connections and renders all five views using Streamlit's testing framework. This verifies zero-network startup and dashboard functionality. Actual account authorization, GitHub connection, remote dependency installation, and Community Cloud deployment still occur when you deploy; they have not been claimed as completed here.
