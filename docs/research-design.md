# ETF Pressure Lab: research design

## Decision and hypothesis

When an ETF falls sharply, should a systematic portfolio buy a rebound or stay in cash? We test whether unusual **reported off-exchange short-sale activity** improves this decision beyond price and volume alone. The alternative-data contribution is the primary research question; profitable trading is a result to measure, not a promised outcome.

The proposed mechanism is deliberately conditional: unusually high short-sale activity during a sell-off might accompany temporary liquidity pressure, but could also precede further losses. The data cannot identify investor intent. It does not directly measure ETF creations, redemptions, fund flows, market-maker inventories, short interest, or net buying/selling pressure.

The distinctive combination is an ETF-specific rebound decision, within-asset-group comparisons, a matched FINRA ablation, and capital-constrained evaluation. Neither mean reversion nor FINRA data is claimed as a new invention.

## Research performed before implementation

- Read the [course syllabus](https://github.com/DataTalksClub/stock-markets-analytics-zoomcamp) and module 1–5 README files.
- Inspected the 2025 module-two notebook's feature-engineering code, including its technical-indicator setup, to distinguish our additional FINRA/group-context features and document the portable pandas implementation.
- Read the [project objective, deliverables, and rubric](https://github.com/DataTalksClub/stock-markets-analytics-zoomcamp/blob/main/projects/README.md).
- Retrieved the [2025 attempt-one list](https://courses.datatalks.club/sma-zoomcamp-2025/project/project1/list): 13 submissions at inspection on 2026-11-03.
- Read the README of the leading listed [Stocks Analytics 2025 submission](https://github.com/nathadriele/stocks-analytics-2025) and the [multisource ETF swing-trading submission](https://github.com/glk08909/etf-swing-trading-multisource). The former presents a broad ML trading system; the latter predicts five-day ETF direction with price and macroeconomic features. Our research question and FINRA ablation differ. These checks are a limited originality review, not proof that nobody has ever studied a similar question. No code was copied.
- Verified one FINRA file directly: 2025-01-03, 10,351 lines including the header/footer, with AAPL and SPY present. Then downloaded the research history using the same public file pattern.

## Free data and tools

| Component | Choice | Why |
|---|---|---|
| Daily adjusted OHLCV | Yahoo Finance through yfinance | Course-aligned prices, dividends/splits reflected by provider adjustment |
| Alternative activity | FINRA CNMS daily files | Public consolidated short-sale activity without a paid API key |
| Transformation/storage | Python, pandas, NumPy, Parquet | A single ETF-day table, small local footprint |
| Models | scikit-learn decision tree, random forest, gradient boosting | Course baselines plus a nonlinear comparison, portable installation |
| UI | Streamlit and Plotly | Interactive evidence, signals, costs, and trade inspection |
| Execution | uv, pytest, GitHub Actions, Docker | Locked environment, automated refresh, reproducibility |

FINRA documents [free noncommercial use and important coverage limitations](https://www.finra.org/finra-data/browse-catalog/short-sale-volume). yfinance describes [research/educational use and Yahoo's personal-use data terms](https://ranaroussi.github.io/yfinance/). Free access is not an open-data redistribution license. Source datasets and model artifacts are excluded from Git; users download directly or privately exchange a permitted snapshot. Do not publicly redistribute source data without checking the applicable terms.

## Universe and scale

Forty explicitly listed, unleveraged ETFs in `config/universe.json` span five groups. Sector funds and GDX are all classified as Sector; USO and DBC are commodity products with futures-related risks. Classification is fixed configuration, not a current fundamentals API joined to historical dates.

The selected surviving ETFs were chosen today. This is **not** a point-in-time comprehensive investable universe. Delisted funds are absent; selection and survivorship bias limit generalization. There is no claim to the >1 million combined-row bonus: unique ETF-day observations matter more than padding records or counting unselected FINRA rows.

## Timing and targets

At session t's close, build features from observations through t. Require the corresponding FINRA file before generating an actionable signal. Buy at t+1 open and sell at t+4 open: three open-to-open trading sessions. The continuous target is that adjusted open-to-open return; the classification target is whether it exceeds 0.20%, approximately the default round-trip cost hurdle. Exact simulated net returns use multiplicative costs instead of subtracting a constant.

The historical FINRA file has a trade date but no point-in-time publication/revision timestamps. Backtesting assumes it was available before the following opening. In operation the scheduled job may be late or a file may be absent; an absent file never becomes zero volume. The app shows observed data dates and produces research signals only. A production broker would need an explicit pre-open availability gate, which is outside this project.

## Validation and selection

1. Initial training uses data before 2024. Validate January–June 2024, then expand training and validate July–December 2024.
2. Purge training labels whose exit date reaches each validation boundary. Validation labels crossing their fold's end are also excluded.
3. Compare depths 3 and 5 for each model and each feature set. Select by mean validation Brier score.
4. Select the FINRA model family by that validation score; use the same family for the price-only comparison. Each variant independently tunes its depth on the same folds.
5. Refit using labels completed before 2025. Evaluate from January 2025 onward. No test-driven threshold or strategy optimization is performed. Threshold 0.55 and risk rules are design constants.

Overlapping three-session labels remain dependent within each block. A paired moving-block bootstrap of portfolio return differences uses 10-session blocks, 1,000 draws, seed 42; its interval is descriptive and sensitive to the block choice. Re-running with newer observations extends the historical holdout and does not create a fresh independent experiment. Latest signals retain the frozen pre-2025 fit; they are not a continuously retrained production model. The model reports probability reliability rather than promising calibrated probabilities.

## Strategies and accounting

- **FINRA + price:** buy qualifying sell-offs with probability ≥0.55, ranked by the selected FINRA model.
- **Price only:** identical rules using that model family's price-only variant.
- **Buy the dip:** qualifying sell-offs ranked by daily loss, without ML.
- **SPY buy and hold:** invest initial capital once over the same marking interval, including entry/exit costs.
- **ETF basket buy and hold:** allocate equal initial capital to all 40 ETFs, with no rebalancing and the same entry/exit cost convention. This contextualizes the multi-asset universe; it does not impose the active strategy's three-position limit.

A qualifying sell-off is a daily loss exceeding the ETF's 21-session realized daily volatility. Maximum three positions, at most one per asset group, no repeated position in the same ticker, no borrowing, fractional adjusted-price shares. Each new trade receives at most one-third of current NAV, limited by available cash. Exits occur before new entries at the open. Cash earns zero. Once NAV falls 10% below its running peak, new entries are blocked; existing positions exit on schedule. This conservative circuit breaker can leave the strategy in cash indefinitely because cash earns no recovery return. It is not an intraday stop loss.

Transaction costs default to 10 bps on each purchase/sale; sensitivity covers 0, 5, 10, 25, 50 bps. Costs are a scenario, not reconstructed bid/ask spreads. Adjusted opens represent a total-return-equivalent accounting convention, not executable raw historical quotes or literal dividend cash accounting. Taxes, funding costs, and cash interest are excluded. Portfolio comparisons should consider exposure as well as CAGR.

## Evidence and acceptance

The dashboard reports capital curves, drawdown, CAGR, Sharpe, exposure, trades, model metrics, reliability buckets, and failure examples. Outputs include feature/target correlations, ticker/group breakdowns, a vector event-return screen, exact share/cash simulations, and cost sensitivity. The bootstrap compares FINRA to price-only, not merely to SPY. A weak or negative FINRA result is retained and discussed.

Critical tests change future prices/FINRA observations and verify past features stay identical; independently check target timing; verify exact transaction costs and cash constraints; reject unsafe snapshot paths. The notebook calls the same Python workflow as automation.

Screenshots must be captured from the running app after real results exist, saved in `docs/screenshots`, and linked in the main README. No placeholder screenshots count as evidence.

## Delivery constraints

Local application and Docker are the default. GitHub Actions refreshes downloadable artifacts; nothing commits generated data. Optional [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) is supported directly through the committed derived dashboard report; see the deployment guide. No AWS/GCP/Azure resources, broker execution, or paid APIs are needed. All Git changes remain uncommitted until the user reviews the final simple message. Use the user's configured identity; no co-author trailers.
