# Verification record — 2026-11-03

## Executed locally

- Installed the locked Python 3.12 environment using uv; exported pip requirements from the same lock.
- Downloaded real Yahoo ETF prices and 1,465 FINRA session files. Verified 58,600 unique combined rows, 40 ETFs, and 100% selected-universe FINRA coverage.
- Completed the CLI pipeline with all six model/feature-set combinations, validation-only selection, simulations, diagnostics, and cost sensitivity.
- Executed the full notebook from cached input; all five code cells completed successfully and reproduced the reported input hash and results.
- Passed **19 pytest tests**: research/accounting checks, report validation, clean-checkout offline rendering of all views, and publication/privacy guards.
- Passed Ruff lint for modules, tests, screenshot script, and app; formatted the Python files and checked Git whitespace.
- Exported the data snapshot, restored it to a temporary directory, and verified identical SHA-256 of the combined input.
- Started the real Streamlit application on localhost. Browser smoke tests passed all five views with no application exceptions. Captured desktop screenshots and a mobile viewport screenshot; visually inspected overview, model evidence, signals, and mobile rendering.
- Confirmed downloaded inputs, model outputs, snapshot archives, and the virtual environment are ignored by Git.
- Added a 361 KB derived presentation report for plug-and-play Community Cloud startup, with no secrets or external storage. Verified dependency discovery against Streamlit's documentation. The hosted view is labeled as a published snapshot rather than a live feed.
- Audited intended publication files, published branch history, notebook outputs, PNG metadata, and workflow exports. The initial commit author-email correction was approved and is applied before the final publication audit. See [publication safety](publication-safety.md).

The notebook ran before a final benchmark-cost precision correction. Benchmark reports were regenerated and the added exact-accounting regression test passed; the displayed two-decimal results and the active-strategy findings are unchanged.

## Limits of verification

- Docker client is installed, but its local daemon was unavailable. The Dockerfile was reviewed; image build and container runtime were **not** executed.
- GitHub Actions definitions are present but have not run remotely because the work has not been committed or pushed.
- No cloud deployment, broker account, or brokerage order was created. Optional hosting instructions do not count as a deployment.
- Source access works in this environment, but future rate limits, schema changes, and provider revisions remain possible. The saved snapshot is the exact reproduction input; a fresh public-source download need not have the same hash.
- NumPy/exchange-calendar deprecation notices appeared; they did not prevent the tests or research run. Sandboxed Arrow capability probes printed OS-permission notices during CLI work, without affecting output. They are dependency/runtime messages rather than suppressed application failures.

## Git handoff

Publication uses only the user's configured Git identity with a GitHub noreply email and no co-author trailers. The approved initial-history correction preserves its original contents, message, and author name. The project commit message is `Add ETF Pressure Lab project`. The push uses an explicit `--force-with-lease` bound to the previously observed remote commit.
