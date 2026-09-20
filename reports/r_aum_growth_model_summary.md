# R AUM Growth Model Summary

Generated on: 2026-09-20

## Purpose

This analysis uses R to explore account-level monthly AUM growth patterns in the synthetic wealth-management baseline. It supports the finance analytics story by showing how statistical analysis can sit beside the Python QA and reporting pipeline.

This is not a production forecasting model. It is an exploratory reporting artifact that helps frame advisor, fee, and segment relationships before downstream stakeholder reporting.

## Data Used

- Advisors file: C:/Users/jayso/.vscode/internships projects/wealth-management-analytics-qa/data/raw/synthetic/synthetic_advisors.csv
- Accounts file: C:/Users/jayso/.vscode/internships projects/wealth-management-analytics-qa/data/raw/synthetic/synthetic_accounts.csv
- Monthly performance file: C:/Users/jayso/.vscode/internships projects/wealth-management-analytics-qa/data/raw/synthetic/synthetic_monthly_performance.csv
- Joined account-month rows used: 269,772
- Distinct advisors: 594
- Distinct accounts: 22,481

## Model Formula

`aum_growth_rate ~ advisor_tenure_years + fee_rate + client_segment + primary_client_segment`

AUM growth rate is calculated as `(ending_aum - beginning_aum) / beginning_aum`.

## Coefficient Summary

| term | estimate | std.error | statistic | p.value |
| --- | --- | --- | --- | --- |
| (Intercept) |  0.00240 | 0.00108 |  2.21953 | 0.02645 |
| advisor_tenure_years | -0.00001 | 0.00002 | -0.39946 | 0.68956 |
| fee_rate | -0.00629 | 0.10290 | -0.06114 | 0.95125 |
| client_segmentemerging_affluent |  0.00039 | 0.00056 |  0.70794 | 0.47898 |
| client_segmenthigh_net_worth |  0.00006 | 0.00058 |  0.10301 | 0.91796 |
| client_segmentinstitutional |  0.00051 | 0.00090 |  0.56406 | 0.57272 |
| primary_client_segmentemerging_affluent | -0.00069 | 0.00051 | -1.34040 | 0.18012 |
| primary_client_segmenthigh_net_worth | -0.00027 | 0.00050 | -0.54183 | 0.58794 |
| primary_client_segmentinstitutional |  0.00001 | 0.00072 |  0.01638 | 0.98693 |

## Confidence Intervals

| term | estimate | conf.low | conf.high | p.value |
| --- | --- | --- | --- | --- |
| (Intercept) |  0.00240 |  0.00028 | 0.00452 | 0.02645 |
| advisor_tenure_years | -0.00001 | -0.00004 | 0.00003 | 0.68956 |
| fee_rate | -0.00629 | -0.20797 | 0.19538 | 0.95125 |
| client_segmentemerging_affluent |  0.00039 | -0.00070 | 0.00149 | 0.47898 |
| client_segmenthigh_net_worth |  0.00006 | -0.00107 | 0.00119 | 0.91796 |
| client_segmentinstitutional |  0.00051 | -0.00125 | 0.00226 | 0.57272 |
| primary_client_segmentemerging_affluent | -0.00069 | -0.00169 | 0.00032 | 0.18012 |
| primary_client_segmenthigh_net_worth | -0.00027 | -0.00126 | 0.00072 | 0.58794 |
| primary_client_segmentinstitutional |  0.00001 | -0.00140 | 0.00142 | 0.98693 |

## Residual Diagnostics Summary

| observation_count | r_squared | adjusted_r_squared | residual_std_error | residual_mean | residual_sd | max_abs_standardized_residual | max_cooks_distance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 269772 | 1e-05 | -2e-05 | 0.0834 | 0 | 0.0834 | 12.02472 | 0.00146 |

Residual diagnostics plot:

- `outputs/r/residuals_vs_fitted.png`

## Client Segment Summary

| client_segment | account_month_rows | avg_aum_growth_rate | median_aum_growth_rate |
| --- | --- | --- | --- |
| affluent | 86436 | 0.00210 | 0.00766 |
| emerging_affluent | 77232 | 0.00209 | 0.00785 |
| high_net_worth | 78816 | 0.00203 | 0.00764 |
| institutional | 27288 | 0.00266 | 0.00769 |

Client-segment plot:

- `outputs/r/aum_growth_by_segment.png`

## Key Takeaways

- The model gives a concise way to inspect whether tenure, fee rate, and client segment are associated with monthly AUM growth in the generated baseline.
- Coefficients should be interpreted directionally and cautiously because the data is synthetic.
- Residual diagnostics help show whether the linear model is leaving visible structure unexplained.
- This R artifact complements the main Python QA layer by adding a finance-analysis lens to the same reporting domain.

## Limitations

- The data is synthetic, so coefficients do not describe real adviser behavior or real client outcomes.
- The model is exploratory and should not be presented as production machine learning or a deployable forecasting tool.
- The formula is intentionally simple and does not account for market benchmarks, nested account/advisor effects, serial correlation, or branch-level structure.
- Seeded-error QA remains the project's main technical depth; this model supports the analytics story without replacing the QA evaluation layer.
