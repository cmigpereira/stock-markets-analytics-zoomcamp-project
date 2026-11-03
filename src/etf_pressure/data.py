"""Public downloads with resumable, ticker-filtered caches and provenance."""

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]


def universe():
    return json.loads((ROOT / "config/universe.json").read_text())


def sessions(start, end):
    """End is exclusive; only request exchange sessions, including exceptional closures."""
    cal = xcals.get_calendar(
        "XNYS",
        start=pd.Timestamp(start) - pd.Timedelta(days=10),
        end=pd.Timestamp(end) + pd.Timedelta(days=10),
    )
    return cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1)).tz_localize(
        None
    )


def finra_day(day, directory, tickers):
    stamp = day.strftime("%Y%m%d")
    target = directory / f"{stamp}.parquet"
    if target.exists():
        return pd.read_parquet(target)
    url = f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{stamp}.txt"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=40)
            r.raise_for_status()
            if not r.text.startswith("Date|Symbol|"):
                raise ValueError("Unexpected FINRA schema")
            frame = pd.read_csv(StringIO(r.text), sep="|", dtype={"Symbol": str})
            frame = frame[frame.Symbol.isin(tickers)].copy()
            frame["date"] = pd.to_datetime(frame.Date.astype(str), format="%Y%m%d")
            frame = frame.rename(
                columns={
                    "Symbol": "ticker",
                    "ShortVolume": "short_volume",
                    "ShortExemptVolume": "exempt_volume",
                    "TotalVolume": "finra_volume",
                }
            )
            frame = frame[["date", "ticker", "short_volume", "exempt_volume", "finra_volume"]]
            if frame.empty or frame.duplicated(["date", "ticker"]).any():
                raise ValueError("Empty or duplicate FINRA observations")
            frame.to_parquet(target, index=False)
            (directory / f"{stamp}.json").write_text(
                json.dumps(
                    {
                        "url": url,
                        "sha256": hashlib.sha256(r.content).hexdigest(),
                        "retrieved_utc": pd.Timestamp.now(tz="UTC").isoformat(),
                        "source_rows": len(r.text.splitlines()) - 2,
                        "selected_rows": len(frame),
                    },
                    indent=2,
                )
            )
            return frame
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def download(start="2021-01-01", end=None, data_dir="data", workers=8):
    end = end or (date.today() + timedelta(days=1)).isoformat()
    directory = Path(data_dir)
    raw = directory / "finra"
    raw.mkdir(parents=True, exist_ok=True)
    mapping = universe()
    price_path = directory / "prices.parquet"
    old = pd.read_parquet(price_path) if price_path.exists() else pd.DataFrame()
    # Refresh a trailing window to incorporate provider revisions without downloading all history.
    price_start = start
    if not old.empty and old.date.min() <= pd.Timestamp(start):
        price_start = max(pd.Timestamp(start), old.date.max() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    prices = yf.download(
        list(mapping),
        start=price_start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=4,
        group_by="ticker",
    )
    parts = []
    for ticker in mapping:
        part = prices[ticker].dropna(subset=["Open", "Close"]).reset_index()
        part.columns = [str(c).lower() for c in part.columns]
        part["date"] = pd.to_datetime(part.date).dt.tz_localize(None)
        part["ticker"] = ticker
        parts.append(part[["date", "ticker", "open", "high", "low", "close", "volume"]])
    new = pd.concat(parts, ignore_index=True)
    if new.empty:
        raise RuntimeError("No Yahoo prices returned; check network/provider limits")
    if not old.empty:
        new = pd.concat([old[old.date < pd.Timestamp(price_start)], new], ignore_index=True)
    new = new.drop_duplicates(["date", "ticker"], keep="last").sort_values(["date", "ticker"])
    absent = set(mapping) - set(new.ticker)
    if absent:
        raise RuntimeError(f"Price history missing for {sorted(absent)}")
    new.to_parquet(price_path, index=False)
    # Only dates with actual prices; future dates never generate fabricated observations.
    days = sessions(start, min(pd.Timestamp(end), new.date.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(finra_day, day, raw, set(mapping)): day for day in days}
        for count, job in enumerate(as_completed(jobs), 1):
            try:
                job.result()
            except Exception as exc:
                failures.append({"date": str(jobs[job].date()), "error": str(exc)})
            if count % 100 == 0:
                print(f"FINRA {count}/{len(days)} sessions; {len(failures)} unavailable", flush=True)
    finra = pd.concat(
        [
            pd.read_parquet(raw / f"{d:%Y%m%d}.parquet")
            for d in days
            if (raw / f"{d:%Y%m%d}.parquet").exists()
        ],
        ignore_index=True,
    )
    combined = new[(new.date >= pd.Timestamp(start)) & (new.date < pd.Timestamp(end))].merge(
        finra, on=["date", "ticker"], how="left", validate="one_to_one"
    )
    combined["asset_class"] = combined.ticker.map(mapping)
    combined.to_parquet(directory / "combined.parquet", index=False)
    manifest = {
        "requested_start": start,
        "requested_end_exclusive": end,
        "price_rows": len(combined),
        "finra_rows": len(finra),
        "finra_coverage": float(combined.short_volume.notna().mean()),
        "unavailable_sessions": failures,
        "universe": mapping,
        "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "last_price_date": str(combined.date.max().date()),
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    if manifest["finra_coverage"] < 0.95:
        raise RuntimeError("FINRA coverage below 95%; inspect data/manifest.json and retry")
    return combined
