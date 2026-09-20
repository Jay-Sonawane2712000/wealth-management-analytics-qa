# R AUM Growth Analysis

This folder contains an exploratory R analysis for account-level monthly AUM growth in the synthetic wealth-management dataset.

The script joins:

- `data/raw/synthetic/synthetic_advisors.csv`
- `data/raw/synthetic/synthetic_accounts.csv`
- `data/raw/synthetic/synthetic_monthly_performance.csv`

It calculates account/month AUM growth rate and fits this model:

```r
aum_growth_rate ~ advisor_tenure_years + fee_rate + client_segment + primary_client_segment
```

## Required Packages

R must be installed with `Rscript` available on your PATH.

The script uses:

- `readr`
- `dplyr`
- `ggplot2`
- `broom`

Install them in R with:

```r
install.packages(c("readr", "dplyr", "ggplot2", "broom"))
```

## Run

If the synthetic CSVs do not exist yet, generate them first:

```bash
python -m ingestion.generate_synthetic
```

Then run the R analysis:

```bash
Rscript r/advisor_aum_growth_model.R
```

## Expected Outputs

- `reports/r_aum_growth_model_summary.md`
- `outputs/r/residuals_vs_fitted.png`
- `outputs/r/aum_growth_by_segment.png`

The analysis is intentionally exploratory. Because the input data is synthetic, the coefficients should not be interpreted as real adviser behavior or used as production forecasting logic.
