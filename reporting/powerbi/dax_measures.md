# Power BI DAX Measures

These measures are starting definitions for the local CSV import model. Table and column names may need adjustment depending on final Power BI import names.

## Financial Measures

```DAX
Total AUM =
SUM ( firm_kpis[ending_aum] )
```

```DAX
Total Revenue =
SUM ( firm_kpis[revenue] )
```

```DAX
Net New Assets =
SUM ( firm_kpis[net_new_assets] )
```

```DAX
AUM Growth Rate =
DIVIDE (
    SUM ( firm_kpis[ending_aum] ) - SUM ( firm_kpis[beginning_aum] ),
    SUM ( firm_kpis[beginning_aum] )
)
```

```DAX
Revenue per Advisor =
DIVIDE (
    SUM ( branch_kpis[revenue] ),
    SUM ( branch_kpis[advisor_count] )
)
```

```DAX
Revenue per Account =
DIVIDE (
    SUM ( firm_kpis[revenue] ),
    SUM ( firm_kpis[account_count] )
)
```

```DAX
Average Fee Rate =
AVERAGE ( firm_kpis[avg_fee_rate] )
```

## QA Measures

```DAX
Injected Error Count =
SUM ( qa_metrics[ground_truth_count] )
```

```DAX
Detection Count =
SUM ( qa_metrics[detection_count] )
```

```DAX
Precision =
DIVIDE (
    SUM ( qa_metrics[true_positives] ),
    SUM ( qa_metrics[true_positives] ) + SUM ( qa_metrics[false_positives] )
)
```

```DAX
Recall =
DIVIDE (
    SUM ( qa_metrics[true_positives] ),
    SUM ( qa_metrics[true_positives] ) + SUM ( qa_metrics[false_negatives] )
)
```

```DAX
False Positive Rate =
DIVIDE (
    SUM ( qa_metrics[false_positives] ),
    SUM ( qa_metrics[detection_count] )
)
```

```DAX
F1 Score =
DIVIDE (
    2 * [Precision] * [Recall],
    [Precision] + [Recall]
)
```

```DAX
Hard Rule Detections =
CALCULATE (
    SUM ( qa_metrics[detection_count] ),
    qa_metrics[detection_family] = "hard_rule"
)
```

```DAX
Statistical Rule Detections =
CALCULATE (
    SUM ( qa_metrics[detection_count] ),
    qa_metrics[detection_family] = "statistical_rule"
)
```

For QA cards, filter `qa_metrics[evaluation_scope]` to `overall` when showing portfolio-level performance.
