# Power BI Dashboard Layout

This is a build specification for a future Power BI report. No `.pbix` file is included in this repository.

## Page 1: Executive Finance Overview

Purpose: summarize the clean baseline financial reporting story for business stakeholders.

Visuals:

- KPI cards: Total AUM, Total Revenue, Net New Assets, AUM Growth Rate.
- AUM trend: line chart by `month_end_date` using Total AUM.
- Revenue trend: column or line chart by `month_end_date` using Total Revenue.
- Branch ranking: bar chart of top branches by revenue or ending AUM.
- Segment breakdown: if segment fields are added to the model later, show AUM or account count by client segment.

Suggested slicers:

- Month
- Firm CRD number
- Branch region

## Page 2: Advisor / Branch Performance

Purpose: support performance review across advisors and branches.

Visuals:

- Advisor table: advisor name, branch, account count, ending AUM, revenue, average fee rate, AUM growth rate.
- Branch comparison: clustered bar chart for revenue, ending AUM, and net new assets by branch.
- Fee rate distribution: histogram or box-style visual using average fee rate.
- Top/bottom advisor slicers: use ranking filters for top and bottom advisors by revenue, AUM growth, or net new assets.

Suggested slicers:

- Month
- Branch
- Advisor
- Firm

## Page 3: QA & Anomaly Review

Purpose: make QA evaluation a first-class business reporting view instead of hidden technical output.

Visuals:

- Precision card.
- Recall card.
- False Positive Rate card.
- F1 Score card.
- Detection family breakdown: stacked bar chart for hard-rule and statistical-rule detections.
- Threshold comparison: matrix or line chart comparing precision, recall, false-positive rate, and F1 score by `threshold_label`.
- Findings table: detection family, rule name, true positives, false positives, false negatives, detection count.
- Reviewer tradeoff note: text box explaining that lower thresholds may catch more issues but can increase reviewer workload.

Suggested slicers:

- Threshold label
- Detection family
- Rule name

Reviewer tradeoff note:

Use this page to discuss the operating threshold in terms of business review capacity. The goal is not only high recall; it is a practical balance between catching bad finance data and avoiding excessive false positives.
