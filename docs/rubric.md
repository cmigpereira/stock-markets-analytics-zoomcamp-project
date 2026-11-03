# Evaluation evidence

Use the [official rubric](https://github.com/DataTalksClub/stock-markets-analytics-zoomcamp/blob/main/projects/README.md#evaluation-criteria) as the authority. This is an evidence map, not a claimed grade.

| Area | Where to inspect our implementation |
|---|---|
| Problem | README and research design: concrete ETF rebound question, motivation, originality review, limitations |
| Sources | Public-source downloader, provenance, dictionary of 48 numeric predictors; FINRA supplements course-aligned Yahoo prices |
| Transformation/EDA | Single ETF-day table; indicator, group, ratio, interaction and event features; target correlations and distributions |
| Modeling | Decision tree, random forest, gradient boosting; two-depth temporal tuning; fixed probability filter; FINRA removal comparison |
| Simulation | Vector event screen plus three capital-constrained strategies; reinvestment, risk controls, benchmark, cost scenarios, failure analysis |
| Automation | Shared module/CLI/notebook workflow; locked dependencies; scheduled refresh; cached snapshot mode; incremental local storage |
| Extras | Modular code, dashboard and operational guide, Docker definition, actual screenshots |

Deliberately unclaimed: million-row dataset, broker integration, cloud deployment, guaranteed benchmark outperformance, subjective reviewer bonuses. Docker execution and remote Actions status are recorded separately in verification. The rubric's 36-point ceiling includes outcome-dependent and subjective items; a high score cannot be guaranteed by implementation alone. Reviewers may interpret novelty and feature increments differently.

Also follow the course's data exclusion rule and complete the required peer reviews when submitting. The linked project README includes historical submission dates; confirm your own cohort/attempt deadline in the course portal rather than treating those dates as current.
