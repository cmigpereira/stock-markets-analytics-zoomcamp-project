"""One workflow shared by CLI, notebook, cron, and GitHub Actions."""

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from etf_pressure.backtest import evaluate
from etf_pressure.data import download
from etf_pressure.features import BASE, FLOW, build_features
from etf_pressure.modeling import train


def run(mode="cached", start="2021-01-01", end=None, data_dir="data", output="artifacts"):
    data, out = Path(data_dir), Path(output)
    out.mkdir(parents=True, exist_ok=True)
    if mode == "download":
        raw = download(start, end, data_dir)
    else:
        if not (data / "combined.parquet").exists():
            raise FileNotFoundError(
                "No local snapshot. Run etf-pressure run --mode download first, or restore a trusted snapshot."
            )
        raw = pd.read_parquet(data / "combined.parquet")
    features = build_features(raw)
    features.to_parquet(data / "features.parquet", index=False)
    predictions, model_report = train(features, output)
    curves, trades, summaries, vector = evaluate(raw, predictions)
    curves.to_parquet(out / "curves.parquet", index=False)
    trades.to_csv(out / "trades.csv", index=False)
    summaries.to_csv(out / "performance.csv", index=False)
    (out / "vector.json").write_text(json.dumps(vector, indent=2))
    sensitivity = []
    for cost in [0, 5, 10, 25, 50]:
        _, _, summary, _ = evaluate(raw, predictions, cost)
        summary["cost_bps_per_side"] = cost
        sensitivity.append(summary)
    pd.concat(sensitivity).to_csv(out / "cost_sensitivity.csv", index=False)
    eda = features[BASE + FLOW + ["target_return"]].corr()["target_return"].drop("target_return")
    eda.rename("correlation").sort_values().to_csv(out / "correlations.csv")
    features.groupby("ticker")[BASE + FLOW].agg(["mean", "std"]).to_csv(out / "feature_summary.csv")
    predictions["probability_bucket"] = pd.cut(
        predictions.p_flow, [0, 0.4, 0.5, 0.55, 0.6, 0.7, 1], include_lowest=True
    )
    diagnostics = predictions.groupby("probability_bucket", observed=True).agg(
        count=("target_win", "size"),
        predicted=("p_flow", "mean"),
        actual=("target_win", "mean"),
        return_mean=("target_return", "mean"),
    )
    diagnostics.to_csv(out / "calibration.csv")
    for name in ["ticker", "asset_class"]:
        predictions.groupby(name).agg(
            count=("target_win", "size"),
            hit_rate=("target_win", "mean"),
            mean_probability=("p_flow", "mean"),
            mean_return=("target_return", "mean"),
        ).to_csv(out / f"by_{name}.csv")
    errors = predictions[predictions.selloff.eq(1)].sort_values("target_return").head(25)
    errors[["date", "ticker", "asset_class", "p_flow", "p_price", "short_z_21", "target_return"]].to_csv(
        out / "worst_predictions.csv", index=False
    )
    # Moving-block bootstrap of paired portfolio daily returns; descriptive, not a significance guarantee.
    wide = curves.pivot(index="date", columns="strategy", values="equity").pct_change().dropna()
    diff = (wide["FINRA + price"] - wide["Price only"]).to_numpy()
    rng = np.random.default_rng(42)
    samples = []
    for _ in range(1000):
        starts = rng.integers(0, max(len(diff) - 10 + 1, 1), size=int(np.ceil(len(diff) / 10)))
        sample = np.concatenate([diff[s : s + 10] for s in starts])[: len(diff)]
        samples.append(sample.mean() * 252)
    ci = np.quantile(samples, [0.025, 0.975]).tolist()
    manifest = json.loads((data / "manifest.json").read_text())
    summary = {
        "raw_rows": len(raw),
        "feature_rows": len(features),
        "test_rows": len(predictions),
        "features": len(BASE + FLOW) + 1,
        "selected_model": model_report["selected_family"],
        "last_date": str(raw.date.max().date()),
        "first_date": str(raw.date.min().date()),
        "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "finra_coverage": manifest["finra_coverage"],
        "paired_annualized_mean_difference_ci95": ci,
        "snapshot_sha256": hashlib.sha256((data / "combined.parquet").read_bytes()).hexdigest(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return summary


def snapshot(destination="artifacts/research-snapshot.zip", data_dir="data"):
    """Only data, never serialized executable models; safe restoration checks file names."""
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ["combined.parquet", "manifest.json"]:
            archive.write(Path(data_dir) / name, name)
    return target


def restore(source, data_dir="data"):
    target = Path(data_dir)
    target.mkdir(parents=True, exist_ok=True)
    allowed = {"combined.parquet", "manifest.json"}
    with zipfile.ZipFile(source) as archive:
        if set(archive.namelist()) != allowed:
            raise ValueError("Snapshot must contain only combined.parquet and manifest.json")
        for name in allowed:
            (target / name).write_bytes(archive.read(name))
