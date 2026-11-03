"""Share/cash ledger and independent vector screening. All returns include idle cash."""

import numpy as np
import pandas as pd


def metrics(equity):
    returns = equity.pct_change().fillna(0)
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / 252)
    peak = equity.cummax()
    return {
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1),
        "cagr": float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1),
        "sharpe": float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() else 0.0,
        "max_drawdown": float((equity / peak - 1).min()),
    }


def simulate(raw, predictions, probability="p_flow", cost_bps=10.0, initial=100_000.0, slots=3):
    """Buy at most three ETFs, max 1/3 NAV each; hold three open-to-open sessions.

    Values use adjusted opens (fractional total-return-equivalent shares). A 10% drawdown
    blocks new entries, but existing positions still follow their original exit schedule.
    ETF overlap is limited to one holding per asset class. No borrowing or short selling.
    """
    price = raw.pivot(index="date", columns="ticker", values="open").sort_index()
    start = predictions.entry_date.min()
    end = predictions.exit_date.max()
    price = price.loc[(price.index >= start) & (price.index <= end)]
    signals = {day: g for day, g in predictions.groupby("entry_date")}
    positions, ledger, history = {}, [], []
    cash, peak = float(initial), float(initial)
    fee = cost_bps / 10000
    # Pre-entry capital is part of the curve, preserving first-trade transaction costs.
    history.append(
        {
            "date": price.index[0] - pd.Timedelta(days=1),
            "equity": cash,
            "cash": cash,
            "positions": 0,
            "exposure": 0.0,
        }
    )
    for day, marks in price.iterrows():
        for ticker, position in list(positions.items()):
            if day >= position["exit_date"]:
                if pd.isna(marks[ticker]):
                    raise ValueError(f"Missing exit mark for {ticker} {day}")
                proceeds = position["shares"] * marks[ticker]
                cash += proceeds * (1 - fee)
                ledger.append(
                    {
                        **position,
                        "ticker": ticker,
                        "exit_date": day,
                        "exit_price": marks[ticker],
                        "pnl": proceeds * (1 - fee) - position["spent"],
                        "net_return": proceeds * (1 - fee) / position["spent"] - 1,
                    }
                )
                del positions[ticker]

        def value():
            if any(pd.isna(marks[t]) for t in positions):
                raise ValueError(f"Missing holding price on {day}")
            return cash + sum(p["shares"] * marks[t] for t, p in positions.items())

        nav = value()
        peak = max(peak, nav)
        candidates = signals.get(day, pd.DataFrame())
        if not candidates.empty and nav >= peak * 0.9:
            candidates = candidates[candidates.selloff.eq(1)].copy()
            if probability != "heuristic":
                candidates = candidates[candidates[probability] >= 0.55].sort_values(
                    probability, ascending=False
                )
            else:
                candidates = candidates.sort_values("ret_1")
            for row in candidates.itertuples():
                classes = {p["asset_class"] for p in positions.values()}
                if len(positions) >= slots:
                    break
                if row.ticker in positions or row.asset_class in classes or pd.isna(marks[row.ticker]):
                    continue
                budget = min(nav / slots, cash)
                if budget < 100:
                    continue
                shares = budget / (marks[row.ticker] * (1 + fee))
                positions[row.ticker] = {
                    "entry_date": day,
                    "exit_date": row.exit_date,
                    "entry_price": marks[row.ticker],
                    "shares": shares,
                    "spent": budget,
                    "asset_class": row.asset_class,
                    "probability": getattr(row, probability, np.nan),
                }
                cash -= budget
        nav = value()
        history.append(
            {
                "date": day,
                "equity": nav,
                "cash": cash,
                "positions": len(positions),
                "exposure": (nav - cash) / nav,
            }
        )
        if cash < -1e-6:
            raise AssertionError("Negative cash violates capital constraints")
    return pd.DataFrame(history).set_index("date"), pd.DataFrame(ledger)


def evaluate(raw, predictions, cost_bps=10.0):
    curves, trades, summaries = [], [], []
    for name, column in [
        ("FINRA + price", "p_flow"),
        ("Price only", "p_price"),
        ("Buy the dip", "heuristic"),
    ]:
        curve, ledger = simulate(raw, predictions, column, cost_bps)
        curve["strategy"] = name
        curves.append(curve.reset_index())
        if not ledger.empty:
            ledger["strategy"] = name
            trades.append(ledger)
        summaries.append(
            {
                "strategy": name,
                **metrics(curve.equity),
                "trades": len(ledger),
                "mean_exposure": float(curve.exposure.mean()),
                "win_rate": float(ledger.net_return.gt(0).mean()) if len(ledger) else 0.0,
            }
        )
    index = curves[0].date
    panel = raw.pivot(index="date", columns="ticker", values="open").reindex(index.iloc[1:])
    basket = panel.div(panel.iloc[0]).mean(axis=1)
    for name, series in [
        ("SPY buy & hold", raw[raw.ticker.eq("SPY")].set_index("date").open),
        ("ETF basket buy & hold", basket),
    ]:
        p = series.reindex(index)
        p.iloc[0] = p.iloc[1]
        equity = 100000 * p / p.iloc[1] / (1 + cost_bps / 10000)
        equity.iloc[0] = 100000
        equity.iloc[-1] *= 1 - cost_bps / 10000
        curve = pd.DataFrame({"date": index, "equity": equity.to_numpy(), "strategy": name})
        curves.append(curve)
        summaries.append(
            {
                "strategy": name,
                **metrics(pd.Series(equity.to_numpy(), index=index)),
                "trades": 1,
                "mean_exposure": 1.0,
                "win_rate": float(equity.iloc[-1] > 100000),
            }
        )
    # This is an event-return screening statistic, not a compounded capital return.
    vector = []
    for name, col in [("FINRA + price", "p_flow"), ("Price only", "p_price")]:
        mask = predictions.selloff.eq(1) & predictions[col].ge(0.55)
        event_returns = (1 + predictions.loc[mask, "target_return"]) * (1 - cost_bps / 10000) / (
            1 + cost_bps / 10000
        ) - 1
        vector.append(
            {
                "strategy": name,
                "events": int(mask.sum()),
                "mean_net_event_return": float(event_returns.mean()) if len(event_returns) else None,
            }
        )
    return (
        pd.concat(curves, ignore_index=True),
        pd.concat(trades, ignore_index=True) if trades else pd.DataFrame(),
        pd.DataFrame(summaries),
        vector,
    )
