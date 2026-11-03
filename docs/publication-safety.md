# Public repository audit

The audit covers intended publication files (tracked and nonignored untracked files), the publication branch's reachable Git file history, notebook text and outputs, dashboard JSON, PNG text/EXIF metadata, workflow artifact exports, and Git email settings. Matching values are never printed by the audit script.

## Current findings

No credential signatures, private home paths, email addresses in file contents, unexpected binary files, or image text/EXIF metadata were detected in the intended publication files. The dashboard report contains public-market research outputs and simulated trades with a fixed starting capital; it contains no brokerage account, real personal holdings, or account activity. Raw market downloads, training tables, and executable models remain excluded from Git.

The user approved replacing the pre-existing initial commit's personal email with the configured GitHub noreply address. The corrected initial commit preserves the original file tree, commit message, and author name. Publication uses only the reviewed `main` branch and an explicit `--force-with-lease` bound to the previous remote commit. Personal email values are deliberately not reproduced here.

If the remote was already public, rewriting it reduces future exposure but cannot retract copies, caches, or forks made earlier. The public GitHub username and chosen commit-author name remain part of ordinary public repository attribution.

## Safeguards added

- Git excludes environment variants, Streamlit secrets, local cloud/SSH/agent configuration, key files, logs, raw Parquet/database files, and model binaries.
- Docker context excludes credentials and local data as well, so ignored secrets are not accidentally sent to a builder.
- The web app shows a controlled error rather than exposing a raw exception traceback to visitors.
- The research workflow uploads only `artifacts/dashboard.json`; full input snapshots and serialized models are no longer exported as downloadable workflow artifacts.
- CI checks out full history and runs the publication audit before dependency installation and testing. It blocks on personal author/committer email metadata in the branch being published.
- Regression tests check credential detection, quoted JSON secrets, private-path detection, redacted diagnostics, ignore rules, binary/image metadata handling, and the published report.

## Run before publishing

```bash
python scripts/audit_publication.py
uv run pytest -q
```

The audit uses only the Python standard library and Git. It is a guard for common patterns and publication mistakes, not a guarantee that every possible private detail can be automatically recognized. Review newly added files and screenshots, never add real portfolio/account exports, and do not use `git add -f` to bypass the exclusions. The audit defaults to `HEAD`; use `--ref main` to audit the publication branch explicitly. Internal local tool checkpoint refs are not published; never mirror-push local refs.
