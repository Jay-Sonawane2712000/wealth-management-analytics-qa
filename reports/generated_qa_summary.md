# Generated QA Summary

## Run Timestamp

2026-09-18

## Ground Truth Injected Error Count

Total injected errors: 40

## Error Type Breakdown

| Error Type | Count |
|---|---:|
| duplicate_account_month | 5 |
| extreme_aum_jump_negative | 5 |
| extreme_aum_jump_positive | 5 |
| extreme_revenue_spike | 5 |
| invalid_fee_rate_high | 5 |
| negative_ending_aum | 5 |
| negative_revenue | 5 |
| revenue_on_closed_account | 5 |

## Detection Count Summary

- Hard-rule detections: 31
- Statistical detections: 2764
- Combined detections: 2795

## Overall Metrics

- Precision: 0.011
- Recall: 0.800
- False-positive rate: 0.989
- F1 score: 0.023
- True positives: 32
- False positives: 2763
- False negatives: 8

## Threshold Comparison

| Threshold | Precision | Recall | False Positive Rate | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| z=2.0_iqr=1.5 | 0.006 | 0.800 | 0.994 | 0.011 | 32 | 5632 | 8 |
| z=2.0_iqr=2.0 | 0.006 | 0.800 | 0.994 | 0.012 | 32 | 5190 | 8 |
| z=2.0_iqr=3.0 | 0.007 | 0.775 | 0.993 | 0.013 | 31 | 4556 | 9 |
| z=2.5_iqr=1.5 | 0.010 | 0.800 | 0.990 | 0.020 | 32 | 3205 | 8 |
| z=2.5_iqr=2.0 | 0.011 | 0.800 | 0.989 | 0.023 | 32 | 2763 | 8 |
| z=2.5_iqr=3.0 | 0.014 | 0.775 | 0.986 | 0.028 | 31 | 2129 | 9 |
| z=3.0_iqr=1.5 | 0.010 | 0.775 | 0.990 | 0.020 | 31 | 3084 | 9 |
| z=3.0_iqr=2.0 | 0.012 | 0.775 | 0.988 | 0.023 | 31 | 2642 | 9 |
| z=3.0_iqr=3.0 | 0.015 | 0.750 | 0.985 | 0.029 | 30 | 2008 | 10 |

## Selected Operating Threshold

Selected threshold: `z=3.0_iqr=3.0`

## Reviewer Tradeoff Explanation

The selected threshold is the best current operating point based on generated F1 score, with recall and precision used as tie-breakers. Lower thresholds may catch more injected issues but can increase reviewer workload through false positives. Higher thresholds may reduce review volume but can allow bad finance data to reach reporting.

## Output Locations

- Detailed ignored CSV outputs: `data/qa/evaluation/` and `data/qa/detections/`
- Corrupted synthetic outputs: `data/raw/synthetic_corrupted/`
