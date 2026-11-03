"""Streamlit research cockpit. Start with: uv run streamlit run app.py."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.etf_pressure.dashboard import load_report, source

st.set_page_config(page_title="ETF Pressure Lab", page_icon="◉", layout="wide")
st.markdown(
    """<style>
.stApp {background:#f6f7f9;color:#15263d;}
[data-testid=stSidebar] {background:#10243a;}
[data-testid=stSidebar] * {color:#e8edf4;}
h1,h2,h3 {letter-spacing:-.035em;}
[data-testid=stMetric] {background:white;border:1px solid #e2e7ee;border-radius:12px;padding:18px;}
.eyebrow {font-size:12px;letter-spacing:.18em;color:#087f8c;font-weight:700;}
.lede {max-width:850px;color:#526176;font-size:18px;line-height:1.6;}
.rule {height:1px;background:#dde3eb;margin:24px 0;}
</style>""",
    unsafe_allow_html=True,
)
ROOT = Path(__file__).resolve().parent


@st.cache_data
def read_artifacts(location, version):
    return load_report(location)


with st.sidebar:
    st.markdown("## ◉ Pressure Lab")
    st.caption("ETF RESEARCH / ZOOMCAMP")
    st.divider()
    page = st.radio(
        "Workspace",
        ["Research overview", "Signal explorer", "Model evidence", "Trade ledger", "Data & method"],
    )
    st.divider()
    st.caption("40 ETFs · 5 asset groups\n\nDaily observations · 3-session horizon")
    st.caption("Educational research only. Not financial advice. No orders are placed.")

st.markdown('<div class="eyebrow">ALTERNATIVE DATA / SYSTEMATIC ETF RESEARCH</div>', unsafe_allow_html=True)
st.title("When selling pressure meets a rebound.")
st.markdown(
    '<p class="lede">Can off-exchange short-sale activity help separate a temporary ETF sell-off from a continuing decline? Test the signal, inspect the evidence, and follow every simulated trade.</p>',
    unsafe_allow_html=True,
)
st.info(
    "**Not financial advice.** This project is for educational and research purposes only. "
    "Its predictions, signals, and simulated trades are not recommendations to buy, sell, or hold any investment. "
    "Past performance and backtested results do not guarantee future results. Investing involves risk, "
    "including loss of capital."
)
try:
    report_location, report_version = source(ROOT)
    a = read_artifacts(str(report_location), report_version)
except (OSError, ValueError, KeyError):
    st.error(
        "The research report could not be loaded. Check the deployment logs or restore reports/dashboard.json from the repository."
    )
    st.stop()
s = a["summary"]
if report_location.is_file():
    st.caption(
        "PUBLISHED RESEARCH SNAPSHOT · Results load directly from this repository. This view is not a live market feed."
    )
st.caption(
    f"REAL DATA · {s['first_date']} → {s['last_date']} · Holdout begins 2025-01-01 · Generated {s['created_utc'][:10]}"
)
st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
palette = {
    "FINRA + price": "#058c88",
    "Price only": "#5865ad",
    "Buy the dip": "#e3a13b",
    "SPY buy & hold": "#8c98aa",
    "ETF basket buy & hold": "#ba7a97",
}


def chart(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#314258",
        margin=dict(l=10, r=10, t=30, b=20),
        legend_title_text="",
    )
    st.plotly_chart(fig, width="stretch")


if page == "Research overview":
    perf = a["performance"].set_index("strategy")
    flow, price = perf.loc["FINRA + price"], perf.loc["Price only"]
    cols = st.columns(4)
    cols[0].metric(
        "FINRA strategy CAGR", f"{flow.cagr:.1%}", f"{(flow.cagr - price.cagr) * 100:+.1f} pp vs price only"
    )
    cols[1].metric("Maximum drawdown", f"{flow.max_drawdown:.1%}")
    cols[2].metric("Executed trades", f"{int(flow.trades):,}")
    cols[3].metric("FINRA data coverage", f"{s['finra_coverage']:.1%}")
    if flow.trades < 30:
        st.caption(
            f"Sparse trading evidence: only {int(flow.trades)} FINRA trades. Low exposure and a small sample limit performance conclusions."
        )
    st.subheader("The capital test")
    st.caption("$100,000 initial capital · 10 bps per side · maximum 3 holdings · idle cash earns 0%")
    chart(
        px.line(
            a["curves"],
            x="date",
            y="equity",
            color="strategy",
            color_discrete_map=palette,
            labels={"equity": "Portfolio value ($)", "date": ""},
            height=400,
        )
    )
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Does FINRA add value?")
        delta = flow.cagr - price.cagr
        st.write(
            f"The FINRA strategy's holdout CAGR differs by {delta * 100:+.2f} percentage points from the matched price-only strategy. Both use the same model family and portfolio rules."
        )
        lo, hi = s["paired_annualized_mean_difference_ci95"]
        st.write(
            f"Paired 10-session block bootstrap: 95% interval [{lo:.1%}, {hi:.1%}] for the annualized mean daily return difference."
        )
        st.caption(
            "This interval describes this historical test. It does not establish a causal relationship or future profitability."
        )
    with right:
        st.subheader("A fair comparison")
        st.write(
            "The model family and depth were selected using 2024 validation only. Results from 2025 onward are held out. The price-only model removes all 14 FINRA features."
        )
        st.write(
            "Short-sale volume is transaction activity, not short interest, investor positioning, or direct ETF fund flows."
        )
    st.dataframe(a["performance"], hide_index=True, width="stretch")
elif page == "Signal explorer":
    st.subheader("Latest research signals")
    st.caption(
        "Frozen model trained on labels completed before 2025. A probability is not a calibrated guarantee."
    )
    latest = a["latest"]
    classes = st.multiselect(
        "Asset groups", sorted(latest.asset_class.unique()), default=sorted(latest.asset_class.unique())
    )
    latest = latest[latest.asset_class.isin(classes)].sort_values("p_flow", ascending=False)
    st.dataframe(
        latest[
            [
                "ticker",
                "asset_class",
                "date",
                "p_flow",
                "p_price",
                "ret_1",
                "short_ratio",
                "short_z_21",
                "eligible",
            ]
        ],
        hide_index=True,
        width="stretch",
        column_config={
            "p_flow": st.column_config.ProgressColumn(
                "Rebound probability", min_value=0, max_value=1, format="%.2f"
            ),
            "eligible": "Passes signal filter",
        },
    )
    st.caption(
        "Filter: loss larger than 21-session daily volatility and model probability ≥55%. Portfolio slots, asset-group limits, and drawdown controls may prevent entry."
    )
    chart(
        px.scatter(
            latest,
            x="short_z_21",
            y="ret_1",
            color="asset_class",
            text="ticker",
            labels={
                "short_z_21": "Unusual short-sale activity (21-session z-score)",
                "ret_1": "Daily return",
            },
            height=420,
        )
    )
elif page == "Model evidence":
    st.subheader("Six models. One controlled comparison.")
    experiments = pd.DataFrame(a["models"]["experiments"]).drop(columns="tuning")
    st.dataframe(experiments, hide_index=True, width="stretch")
    st.caption(
        f"Selected family: {a['models']['selected_family']}. Lower Brier is better; AUC 0.5 is random ranking. Baseline holdout Brier: {a['models']['constant_baseline']['brier']:.4f}."
    )
    left, right = st.columns(2)
    with left:
        st.subheader("What the model uses")
        chart(
            px.bar(
                a["importance"].head(15).sort_values("importance"),
                x="importance",
                y="feature",
                orientation="h",
                height=470,
                color_discrete_sequence=["#058c88"],
            )
        )
    with right:
        st.subheader("Probability reliability")
        fig = px.scatter(
            a["calibration"],
            x="predicted",
            y="actual",
            size="count",
            hover_name="probability_bucket",
            height=470,
        )
        fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(color="#9aa6b4", dash="dash"))
        fig.update_xaxes(range=[0, 1])
        fig.update_yaxes(range=[0, 1])
        chart(fig)
    st.subheader("Where the hypothesis fails")
    st.dataframe(a["errors"], hide_index=True, width="stretch")
elif page == "Trade ledger":
    st.subheader("Every entry has a cost")
    selection = st.selectbox("Strategy", list(palette)[:3])
    ledger = a["trades"][a["trades"].strategy.eq(selection)]
    st.dataframe(ledger, hide_index=True, width="stretch")
    st.download_button(
        "Download full trade ledger", a["trades"].to_csv(index=False), "trade-ledger.csv", "text/csv"
    )
    st.subheader("Would the result survive higher costs?")
    chart(
        px.line(
            a["costs"],
            x="cost_bps_per_side",
            y="cagr",
            color="strategy",
            markers=True,
            color_discrete_map=palette,
            labels={"cost_bps_per_side": "Trading cost per side (bps)", "cagr": "CAGR"},
            height=380,
        )
    )
else:
    st.subheader("Follow the evidence")
    cols = st.columns(3)
    cols[0].metric("Combined ETF-day rows", f"{s['raw_rows']:,}")
    cols[1].metric("After feature warm-up", f"{s['feature_rows']:,}")
    cols[2].metric("Holdout observations", f"{s['test_rows']:,}")
    st.markdown("""
    **Sources.** Yahoo Finance adjusted OHLCV via yfinance; FINRA consolidated daily short-sale volume files.

    **Timeline.** Observe close and published FINRA file → compute features → next-session open entry → exit three sessions later at the open.
    Historical publication timestamps are unavailable; delayed publication would delay or cancel a live trade.

    **Validation.** Train through 2023, tune on two expanding 2024 folds, refit through 2024, test from 2025. Purge training labels crossing each boundary.

    **Execution.** Fractional shares, no leverage, at most three positions, one position per asset group, equal capital limits, 10 bps per side, no new entries after a 10% portfolio drawdown.

    **Limitations.** Fixed surviving ETF universe; adjusted price revisions; no historical bid/ask quotes; overlapping holdings and labels; no interest on cash or taxes. FINRA measures off-exchange reported transactions, not outstanding shorts or fund creations/redemptions.

    **Reproducibility.** The snapshot hash identifies the exact input. Cached mode makes no data requests. Downloads and generated model files stay outside Git.
    """)
    st.code(s["snapshot_sha256"], language=None)
    st.caption(
        "Full design, feature definitions, commands, and rubric evidence are in the repository docs folder."
    )
