# Measured results — 2026-11-03

**The FINRA features did not improve the tested trading decision.** The selected random forest's FINRA variant produced less portfolio return than its price-only counterpart. Both active ML strategies traded very rarely and lagged the fully invested benchmarks. This is a reproducible negative finding, not evidence of a profitable FINRA-based trading edge.

## What was measured

Real downloads cover **2021-01-04 through 2026-11-02**: 58,600 unique ETF-day rows, 40 ETFs, 1,465 sessions, 100% FINRA coverage. After warm-up there are 56,080 modeled rows and **18,240 labeled holdout observations**. The first holdout signal date is 2025-01-02; the portfolio interval begins with next-open execution on 2025-01-03 and finishes on 2026-11-02. Outcomes for the most recent four sessions are not yet known and do not enter evaluation.

Input SHA-256:

```text
d945c0780480a13d64e05f2b9f23116a490bdee4bb82a29bbe70f141062a6d22
```

Default cost: 10 bps per side; initial capital $100,000; idle cash earns zero. Benchmarks pay initial and terminal trading costs. The basket allocates equal initial capital to all selected ETFs, then holds without rebalancing. The three-position/asset-group constraints apply to the active strategies.

| Strategy | Total return | CAGR | Sharpe | Max drawdown | Completed trades / round trips | Mean capital exposure |
|---|---:|---:|---:|---:|---:|---:|
| FINRA + price | 6.09% | 3.28% | 1.34 | −1.16% | 5 | 1.09% |
| Price only | 19.47% | 10.20% | 1.58 | −2.79% | 12 | 2.62% |
| Buy the dip | −6.65% | −3.69% | −0.39 | −13.00% | 51 | 11.07% |
| SPY buy and hold | 31.54% | 16.14% | 0.96 | −19.77% | 1 | 100% |
| ETF basket buy and hold | 34.20% | 17.42% | 1.29 | −12.68% | 1 portfolio round trip | 100% |

The apparent drawdown advantage of the ML strategies is mostly an **exposure difference**: they left almost all capital idle. Five trades are insufficient to infer a stable Sharpe or win rate. The FINRA strategy's 80% trade win rate means four wins and one loss, not a large sample of consistent success. None of these active strategies merits the rubric's exceptional-profitability claim against either benchmark.

## Did the new source add predictive value?

Validation selected a depth-three random forest. Its mean 2024 Brier score was 0.24750 with FINRA and 0.24787 without FINRA. That small validation advantage did not transfer to the holdout Brier score:

| Random forest variant | Holdout AUC | Holdout Brier, lower is better | Precision at probability ≥0.55, all ETF-days |
|---|---:|---:|---:|
| Price only | 0.55773 | 0.24460 | 74.19% |
| FINRA + price | 0.55949 | 0.24480 | 71.43% |

The constant training-prevalence baseline scored 0.24975 Brier and 0.5 AUC. Both models improve slightly on it, but FINRA's AUC gain of about 0.0018 is economically unconvincing here. Classification precision in this table includes non-sell-off days; it is not portfolio trade precision. Only **14** FINRA predictions exceed 0.55 across the entire holdout. Seven also pass the sell-off filter, and position/group constraints reduce execution to five.

The paired 10-session moving-block bootstrap gives a 95% interval of **−14.77% to −1.33%** for the annualized arithmetic mean daily return difference, FINRA minus price only. This is **not** a CAGR interval. With so few active trades, overlapping labels, and an arbitrary block size, it should not be promoted as a robust significance result. The direct observed CAGR difference is −6.92 percentage points.

## Why the hypothesis struggled

1. **The model usually stays near or below 0.50.** The 0.55 threshold leaves very few opportunities. In the (0.50, 0.55] bucket, there are 880 observations with an average predicted probability of 0.518 and observed event rate of 0.575. The above-0.55 bucket has just 14 observations. Reliability therefore varies by region and cannot be treated as a calibrated live probability.
2. **Volatility and asset class dominate.** The leading impurity importances are 63-session volatility, 21-session volatility, daily range, the bond-group indicator, short-term volatility, and SPY volatility. FINRA variables do not dominate the selected shallow forest. Impurity importance is model-specific and not causal evidence.
3. **The return hurdle is harder for bonds.** Bond ETF observations exceed the 0.20% three-session hurdle only 35.46% of the time, versus 53.73% for commodities. A common return hurdle and probability cutoff favor volatile groups. This helps explain group differences without claiming that one group is intrinsically more predictable.
4. **The missed opportunities matter.** FINRA executed XLY, GDX, GLD, and DBC trades. The price-only strategy also captured additional SLV, FXI, USO, and SMH opportunities. Its 2026-06-11 GDX trade returned about 16.20% net on the allocated trade capital and was absent from the FINRA strategy. A handful of large outcomes drives the difference; it is not broad proof of price-only superiority.
5. **A concrete failure remains visible.** Both variants bought XLY at the 2025-03-14 open and exited at the 2025-03-19 open, losing about 0.56% after costs. FINRA's predicted probability was only 0.555, a marginal qualifying signal. The available features cannot establish the reason for that loss; attributing it to a particular news event would need separate evidence.
6. **The heuristic's risk control becomes a cash lock.** The unfiltered dip strategy hit the drawdown gate in April 2025. With zero cash interest and no reset rule, it could not recover to its high-water mark and stopped opening positions. This is the implemented rule's behavior, not a simulation failure. A finite cooldown is an experiment for new validation data, not a retrospective repair of this test.

## Costs and uncertainty

The vector screen finds seven FINRA sell-off events with mean net three-session return of 1.91%, versus 17 price-only events at 3.69%. Those are overlapping event averages before portfolio capacity rules; compounding them as if every event had independent capital would be wrong.

`artifacts/cost_sensitivity.csv` evaluates 0–50 bps per side. Increasing costs lowers results, but does not explain the principal gap between variants: trade selection and activity matter more. There are no observed historical spreads, so these are cost scenarios, not broker-fill estimates.

The universe excludes failed/delisted ETFs, provider-adjusted history can be revised, and historical FINRA availability times are assumed. Both the economically small model-metric differences and sparse execution argue for modest conclusions.

## Follow-up experiments, requiring fresh evaluation

- Choose thresholds on validation data with a minimum activity requirement; reserve a genuinely new period for evaluation. Do not tune on the published holdout.
- Compare volatility-scaled return targets or within-group targets so the fixed return hurdle does not largely separate asset classes.
- Add a finite drawdown cooldown as a separately validated strategy; compare against exposure-matched benchmarks and nonzero cash interest.
- Compare feature sets at a matched opportunity rate, repeat with multiple predeclared seeds, and use longer untouched windows before claiming an edge.
- Obtain timestamped publication/correction data if available. Research a separate ETF primary-market source before making any claims about creations/redemptions or mechanism.

## Reproduce this finding

Use the README's fixed-window download command, or restore the matching private snapshot and run cached mode. Match the input hash for an exact data comparison. A later Yahoo re-download can differ because adjusted history changes; preserve the snapshot rather than expecting an immutable public API. No thresholds, strategy rules, or family selection were changed in response to these results. A subsequent notebook execution verifies the same workflow from cached data.
