"""Protect against leakage and accounting mistakes that can manufacture trading profits."""

import numpy as np
import pandas as pd
import pytest

from etf_pressure.backtest import evaluate, simulate
from etf_pressure.features import BASE, FLOW, build_features
from etf_pressure.modeling import training_rows
from etf_pressure.pipeline import restore


@pytest.fixture
def raw():
    rng = np.random.default_rng(15)
    dates = pd.bdate_range("2023-01-02", periods=150)
    frames = []
    for ticker in ["SPY", "TLT"]:
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(dates))))
        frames.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "ticker": ticker,
                    "open": close * 0.998,
                    "close": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "volume": 1000000,
                    "short_volume": rng.integers(200, 800, len(dates)),
                    "finra_volume": 1000,
                    "exempt_volume": 1,
                    "asset_class": "US equity" if ticker == "SPY" else "Bonds",
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def test_future_prices_cannot_change_past_features(raw):
    cutoff = raw.date.sort_values().unique()[100]
    original = build_features(raw)
    changed = raw.copy()
    changed.loc[changed.date > cutoff, ["open", "high", "low", "close", "short_volume"]] *= 2
    altered = build_features(changed)
    a = original[original.date <= cutoff][BASE + FLOW]
    b = altered[altered.date <= cutoff][BASE + FLOW]
    pd.testing.assert_frame_equal(a, b)


def test_target_matches_trade_timing(raw):
    f = build_features(raw)
    row = f[f.ticker.eq("SPY")].iloc[10]
    p = raw[raw.ticker.eq("SPY")].set_index("date")
    assert row.target_return == pytest.approx(
        p.loc[row.exit_date, "open"] / p.loc[row.entry_date, "open"] - 1
    )
    assert len(p.loc[row.entry_date : row.exit_date]) == 4
    assert row.entry_date > row.date


def test_missing_finra_is_not_zero(raw):
    raw.loc[(raw.ticker == "SPY") & (raw.date == raw.date.max()), "short_volume"] = np.nan
    frame = build_features(raw)
    assert frame[(frame.ticker == "SPY") & (frame.date == raw.date.max())].empty


def test_exact_costs_and_capital_constraints():
    dates = pd.bdate_range("2025-01-01", periods=5)
    raw = pd.DataFrame({"date": dates, "ticker": "SPY", "open": 100.0})
    predictions = pd.DataFrame(
        {
            "entry_date": [dates[0]],
            "exit_date": [dates[3]],
            "ticker": ["SPY"],
            "selloff": [1],
            "p_flow": [0.9],
            "asset_class": ["US equity"],
        }
    )
    curve, ledger = simulate(raw, predictions, cost_bps=10, slots=1)
    expected = 100000 / 1.001 * 0.999
    assert curve.equity.iloc[-1] == pytest.approx(expected)
    assert ledger.pnl.sum() == pytest.approx(expected - 100000)
    assert curve.cash.min() >= -1e-8
    assert curve.positions.max() == 1
    assert curve.equity.iloc[0] == 100000


def test_snapshot_rejects_path_traversal(tmp_path):
    import zipfile

    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../bad.txt", "bad")
    with pytest.raises(ValueError, match="only"):
        restore(archive, tmp_path / "data")


def test_selloff_filter_uses_previous_signal_not_same_open():
    dates = pd.bdate_range("2025-01-01", periods=6)
    raw = pd.DataFrame({"date": dates, "ticker": "SPY", "open": [100, 200, 200, 200, 200, 200]})
    predictions = pd.DataFrame(
        {
            "entry_date": [dates[1]],
            "exit_date": [dates[4]],
            "ticker": ["SPY"],
            "selloff": [1],
            "p_flow": [0.9],
            "asset_class": ["US equity"],
        }
    )
    _, ledger = simulate(raw, predictions, cost_bps=0, slots=1)
    assert ledger.entry_price.iloc[0] == 200
    assert ledger.net_return.iloc[0] == 0


def test_training_labels_crossing_boundary_are_purged():
    rows = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-12-24", "2024-12-30", "2025-01-02"]),
            "exit_date": pd.to_datetime(["2024-12-31", "2025-01-03", "2025-01-08"]),
        }
    )
    selected = training_rows(rows, "2025-01-01")
    assert len(selected) == 1
    assert (selected.exit_date < pd.Timestamp("2025-01-01")).all()


def test_group_and_slot_limits_with_competing_signals():
    dates = pd.bdate_range("2025-01-01", periods=5)
    tickers = ["A", "B", "C", "D", "E"]
    raw = pd.DataFrame([{"date": day, "ticker": t, "open": 100.0} for day in dates for t in tickers])
    predictions = pd.DataFrame(
        {
            "entry_date": [dates[0]] * 5,
            "exit_date": [dates[3]] * 5,
            "ticker": tickers,
            "selloff": 1,
            "p_flow": [0.9, 0.8, 0.7, 0.6, 0.56],
            "asset_class": ["equity", "equity", "bond", "metal", "other"],
        }
    )
    curve, ledger = simulate(raw, predictions, cost_bps=0, slots=3)
    assert curve.positions.max() == 3
    assert set(ledger.ticker) == {"A", "C", "D"}
    assert ledger.spent.max() <= 100000 / 3 + 1e-8
    assert curve.cash.min() >= -1e-8


def test_basket_benchmark_has_equal_initial_capital_and_exact_costs():
    dates = pd.bdate_range("2025-01-01", periods=4)
    raw = pd.concat(
        [
            pd.DataFrame({"date": dates, "ticker": "SPY", "open": [100.0, 110.0, 120.0, 130.0]}),
            pd.DataFrame({"date": dates, "ticker": "TLT", "open": [100.0, 90.0, 80.0, 70.0]}),
        ]
    )
    predictions = pd.DataFrame(
        {
            "entry_date": [dates[0]],
            "exit_date": [dates[3]],
            "ticker": ["SPY"],
            "selloff": [0],
            "p_flow": [0.1],
            "p_price": [0.1],
            "asset_class": ["equity"],
            "ret_1": [0.0],
            "target_return": [0.0],
        }
    )
    curves, _, _, _ = evaluate(raw, predictions, cost_bps=10)
    basket = curves[curves.strategy.eq("ETF basket buy & hold")]
    assert basket.equity.iloc[0] == 100000
    assert basket.equity.iloc[-1] == pytest.approx(100000 / 1.001 * 0.999)
