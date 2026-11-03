"""Features are known after session t; targets start at the next session's open."""

import numpy as np
import pandas as pd

BASE = [
    "ret_1",
    "ret_3",
    "ret_5",
    "ret_10",
    "ret_21",
    "vol_5",
    "vol_21",
    "vol_63",
    "vol_ratio",
    "range_pct",
    "close_location",
    "gap",
    "intraday",
    "volume_rel_5",
    "volume_rel_21",
    "dollar_volume_log",
    "sma_5_dist",
    "sma_21_dist",
    "sma_63_dist",
    "drawdown_63",
    "rsi_14",
    "down_streak",
    "spy_ret_1",
    "spy_ret_5",
    "spy_vol_21",
    "relative_ret_5",
    "breadth_down",
    "class_ret_1",
    "class_ret_5",
    "class_dispersion",
    "weekday",
    "month",
    "selloff",
    "risk_high",
]
FLOW = [
    "short_ratio",
    "short_ratio_lag1",
    "short_mean_5",
    "short_mean_21",
    "short_z_21",
    "short_z_63",
    "short_change_1",
    "short_change_5",
    "exempt_ratio",
    "finra_volume_rel",
    "flow_price_interaction",
    "flow_vol_interaction",
    "class_short_z",
    "flow_divergence",
]
DUMMIES = ["asset_class"]
TO_PREDICT = ["target_return", "target_win"]


def build_features(raw):
    parts = []
    for _, g in raw.sort_values(["ticker", "date"]).groupby("ticker"):
        g = g.copy()
        c, v = g.close, g.volume
        r = c.pct_change()
        for n in [1, 3, 5, 10, 21]:
            g[f"ret_{n}"] = c.pct_change(n)
        for n in [5, 21, 63]:
            g[f"vol_{n}"] = r.rolling(n).std()
            g[f"sma_{n}_dist"] = c / c.rolling(n).mean() - 1
        g["vol_ratio"] = g.vol_5 / g.vol_21
        g["range_pct"] = (g.high - g.low) / c
        g["close_location"] = (c - g.low) / (g.high - g.low).replace(0, np.nan)
        g["gap"] = g.open / c.shift() - 1
        g["intraday"] = c / g.open - 1
        for n in [5, 21]:
            g[f"volume_rel_{n}"] = v / v.rolling(n).mean()
        g["dollar_volume_log"] = np.log1p(c * v)
        g["drawdown_63"] = c / c.rolling(63).max() - 1
        gain = r.clip(lower=0).rolling(14).mean()
        loss = -r.clip(upper=0).rolling(14).mean()
        g["rsi_14"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
        down = r.lt(0)
        g["down_streak"] = down.groupby((~down).cumsum()).cumsum().astype(int)
        q = g.short_volume / g.finra_volume.replace(0, np.nan)
        g["short_ratio"] = q
        g["short_ratio_lag1"] = q.shift()
        for n in [5, 21]:
            g[f"short_mean_{n}"] = q.rolling(n, min_periods=n).mean()
        for n in [21, 63]:
            # Compare today's observation with the distribution strictly before today.
            g[f"short_z_{n}"] = (q - q.shift().rolling(n).mean()) / q.shift().rolling(n).std()
        g["short_change_1"] = q.diff()
        g["short_change_5"] = q.diff(5)
        g["exempt_ratio"] = g.exempt_volume / g.finra_volume.replace(0, np.nan)
        g["finra_volume_rel"] = g.finra_volume / g.finra_volume.rolling(21).mean()
        g["flow_price_interaction"] = g.short_z_21 * g.ret_1
        g["flow_vol_interaction"] = g.short_z_21 * g.vol_ratio
        # Three trading sessions: buy t+1 open, sell t+4 open. Open-to-open avoids
        # pretending we can trade the close used to construct today's features.
        g["entry_date"] = g.date.shift(-1)
        g["exit_date"] = g.date.shift(-4)
        g["target_return"] = g.open.shift(-4) / g.open.shift(-1) - 1
        g["target_win"] = (g.target_return > 0.002).where(g.target_return.notna())
        parts.append(g)
    frame = pd.concat(parts).sort_values(["date", "ticker"])
    spy = frame[frame.ticker.eq("SPY")].set_index("date")
    for col in ["ret_1", "ret_5", "vol_21"]:
        frame[f"spy_{col}"] = frame.date.map(spy[col])
    frame["relative_ret_5"] = frame.ret_5 - frame.spy_ret_5
    frame["breadth_down"] = frame.ret_1.lt(0).groupby(frame.date).transform("mean")
    group = frame.groupby(["date", "asset_class"])
    frame["class_ret_1"] = group.ret_1.transform("mean")
    frame["class_ret_5"] = group.ret_5.transform("mean")
    frame["class_dispersion"] = group.ret_1.transform("std").fillna(0)
    frame["class_short_z"] = group.short_z_21.transform("mean")
    frame["flow_divergence"] = frame.short_z_21 - frame.class_short_z
    frame["weekday"] = frame.date.dt.dayofweek
    frame["month"] = frame.date.dt.month
    frame["selloff"] = (frame.ret_1 < -frame.vol_21).astype(int)
    frame["risk_high"] = (frame.spy_vol_21 > 0.015).astype(int)
    frame[BASE + FLOW] = frame[BASE + FLOW].replace([np.inf, -np.inf], np.nan)
    # Require a full warm-up and real FINRA observations; never impute missing days as zero.
    frame = frame[frame.vol_63.notna() & frame.short_z_63.notna()].copy()
    return frame.reset_index(drop=True)
