# QA Evaluation Report

## Purpose

This report summarizes how well hard-rule and statistical QA detections identify seeded financial reporting errors. The goal is measured QA performance, not simply proving that checks exist.

## Ground Truth Summary

Insert generated counts from `ground_truth_injected_errors.csv` here:

- Total injected errors:
- Hard-rule seeded errors:
- Statistical-rule seeded errors:
- Error types represented:

## Detection Families

Hard-rule detections cover deterministic issues such as negative AUM, negative revenue, invalid fee rates, duplicate account-month records, closed-account revenue, missing references, and null keys.

Statistical detections cover unusual AUM growth and revenue patterns using z-score and IQR thresholds.

## Metrics Definitions

Precision = how many flagged records were truly injected issues.

Recall = how many injected issues were caught.

False positives waste reviewer time.

False negatives risk bad numbers reaching Finance.

F1 score balances precision and recall into one summary metric.

## Threshold Comparison

Insert generated threshold-comparison metrics here. Compare z-score and IQR settings such as `z=2.0_iqr=1.5`, `z=2.5_iqr=2.0`, and `z=3.0_iqr=3.0`.

## Selected Operating Threshold

Document the selected threshold after reviewing the generated metrics. The selected threshold should balance reporting accuracy and reviewer workload.

## Reviewer Tradeoff

Lower thresholds may catch more injected issues but create more false positives. Higher thresholds may reduce reviewer workload but risk allowing seeded reporting errors to remain undetected.

## Current Status

The evaluation framework is implemented. Final metric values should be inserted after running the local QA pipeline and reviewing the generated CSV outputs.
