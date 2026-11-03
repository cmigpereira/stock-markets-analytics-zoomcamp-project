"""Portable presentation reports: derived evidence only, with no raw inputs or models."""

import json
from pathlib import Path

import pandas as pd

TABLES = {
    "curves": "curves.parquet",
    "latest": "latest.parquet",
    "performance": "performance.csv",
    "trades": "trades.csv",
    "importance": "importance.csv",
    "calibration": "calibration.csv",
    "costs": "cost_sensitivity.csv",
    "errors": "worst_predictions.csv",
}
LATEST_COLUMNS = [
    "date",
    "ticker",
    "asset_class",
    "p_flow",
    "p_price",
    "ret_1",
    "short_ratio",
    "short_z_21",
    "eligible",
]


def source(root):
    root = Path(root)
    artifacts = root / "artifacts"
    required = ["summary.json", "models.json", *TABLES.values()]
    if all((artifacts / name).is_file() for name in required):
        return artifacts, max((artifacts / name).stat().st_mtime_ns for name in required)
    published = root / "reports/dashboard.json"
    return published, published.stat().st_mtime_ns


def load_report(location):
    location = Path(location)
    if location.is_dir():
        result = {name: json.loads((location / f"{name}.json").read_text()) for name in ["summary", "models"]}
        for name, filename in TABLES.items():
            result[name] = (
                pd.read_parquet(location / filename)
                if filename.endswith("parquet")
                else pd.read_csv(location / filename)
            )
        return result
    report = json.loads(location.read_text())
    if report.get("schema_version") != 1:
        raise ValueError("Unsupported dashboard report version")
    result = {name: report[name] for name in ["summary", "models"]}
    for name in TABLES:
        result[name] = pd.DataFrame(report["tables"][name])
    for name in ["curves", "latest"]:
        result[name]["date"] = pd.to_datetime(result[name]["date"])
    return result


def publish_report(artifacts="artifacts", destination="reports/dashboard.json"):
    report = load_report(artifacts)
    # Keep only the small presentation view, not the unified feature/target source table.
    report["latest"] = report["latest"][LATEST_COLUMNS]
    tables = {
        name: json.loads(report[name].to_json(orient="records", date_format="iso", double_precision=10))
        for name in TABLES
    }
    payload = {
        "schema_version": 1,
        "summary": report["summary"],
        "models": report["models"],
        "tables": tables,
    }
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n")
    temporary.replace(target)
    return target
