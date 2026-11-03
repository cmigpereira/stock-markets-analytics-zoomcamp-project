# Feature dictionary

One row is one ETF and one observed trading date. Prices are provider-adjusted; returns are decimals, volumes are shares. Definitions match `src/etf_pressure/features.py`. Numeric infinities become missing; median imputation is fitted on training data only. ETF ticker and dates are identifiers, never predictors. Forward labels are excluded from every feature list.

`NUMERIC` is represented by the explicit `BASE` and `FLOW` lists; `DUMMIES` contains `asset_class`; `TO_PREDICT` contains the forward return and event label. One-hot encoding is fitted within each training fold, with unknown groups ignored. Warm-up requires 63-session price volatility and a valid 63-session historical short-activity z-score. Median imputation handles remaining isolated indicator gaps, not absent FINRA dates.

## BASE: 34 numeric predictors

| Name | Definition |
|---|---|
| ret_1, ret_3, ret_5, ret_10, ret_21 | Close / close n sessions ago − 1 |
| vol_5, vol_21, vol_63 | Sample standard deviation of daily returns over n sessions |
| vol_ratio | Five-session / 21-session volatility |
| range_pct | (High − low) / close |
| close_location | (Close − low) / (high − low); missing for a zero range |
| gap | Today's open / previous close − 1 |
| intraday | Close / open − 1 |
| volume_rel_5, volume_rel_21 | Volume / trailing n-session average volume |
| dollar_volume_log | log(1 + close × share volume) |
| sma_5_dist, sma_21_dist, sma_63_dist | Close / n-session average close − 1 |
| drawdown_63 | Close / trailing 63-session maximum close − 1 |
| rsi_14 | 100 − 100 / (1 + mean positive daily return / mean absolute negative return), 14-session simple averages; not Wilder smoothing |
| down_streak | Consecutive negative-return sessions ending today |
| spy_ret_1, spy_ret_5 | SPY daily and five-session return, joined on date |
| spy_vol_21 | SPY 21-session daily return volatility |
| relative_ret_5 | ETF five-session return minus SPY five-session return |
| breadth_down | Fraction of the fixed 40-ETF universe with a negative daily return |
| class_ret_1, class_ret_5 | Equal-weight same-day asset-group mean daily / five-session return |
| class_dispersion | Within-group sample standard deviation of daily returns |
| weekday, month | Integer session day of week (Monday=0) and month (January=1) |
| selloff | Indicator: ret_1 < −vol_21 |
| risk_high | Indicator: SPY daily volatility over 21 sessions > 0.015 |

## FLOW: 14 alternative-data predictors

| Name | Definition |
|---|---|
| short_ratio | FINRA ShortVolume / FINRA TotalVolume, both from the same consolidated daily file |
| short_ratio_lag1 | Prior-session short_ratio |
| short_mean_5, short_mean_21 | Trailing 5/21-session mean short_ratio including today |
| short_z_21, short_z_63 | (Today's ratio − historical mean) / historical sample SD, using only the previous 21/63 sessions |
| short_change_1, short_change_5 | Ratio minus its value 1/5 sessions earlier |
| exempt_ratio | FINRA ShortExemptVolume / FINRA TotalVolume; not added to ShortVolume |
| finra_volume_rel | FINRA total volume / trailing 21-session mean FINRA volume |
| flow_price_interaction | short_z_21 × ret_1 |
| flow_vol_interaction | short_z_21 × vol_ratio |
| class_short_z | Mean short_z_21 within today's asset group |
| flow_divergence | ETF short_z_21 minus class_short_z |

The ratio denominator is FINRA's covered volume, **not** consolidated Yahoo trading volume. This avoids presenting a partial-market numerator as a market-wide short-sale fraction. Consolidated CNMS rows are not summed with their component facility files. ShortExemptVolume is retained as a distinct field; do not double-count it.

The [2025 module-two notebook](https://github.com/DataTalksClub/stock-markets-analytics-zoomcamp/blob/main/02-dataframe-analysis/%5B2025%5D_Module_02_Colab_Working_with_the_data.ipynb) was inspected: it covers returns, rolling volatility, technical indicators through TA-Lib, and calendar features. Our implementation uses portable pandas formulas rather than requiring TA-Lib's native installation; the simple-average RSI definition is explicitly different from Wilder smoothing.

We identify 22 research-specific additions: the 14 FLOW predictors plus breadth_down, class_ret_1, class_ret_5, class_dispersion, relative_ret_5, down_streak, close_location, and risk_high. This exceeds a 10% feature-volume increment, even without counting dummy columns separately. Similar concepts can exist in generic indicator libraries; “new” means an extension of the inspected lecture setup, not academic novelty or a guaranteed reviewer decision. The exact numeric schema has 48 predictors and one categorical group before one-hot expansion.

## Targets and execution fields

| Field | Role |
|---|---|
| entry_date | Next observed price session (t+1) |
| exit_date | Fourth next observed price session (t+4) |
| target_return | Adjusted open(t+4) / open(t+1) − 1 |
| target_win | target_return > 0.002; missing while the outcome is unknown |
| p_flow / p_price | Model predictions, never training inputs |
| eligible | Latest sell-off and p_flow ≥0.55; not a guarantee that portfolio capacity allows a trade |

Only observed closed-session information is used. Today's cross-sectional context is available after all selected markets' US-listed ETF sessions close. The target convention excludes the next opening gap, because the strategy cannot capture it after entering at that open.
