# QA Evaluation Report

## Purpose

This report summarizes how well hard-rule and statistical QA detections identify seeded financial reporting errors. The goal is measured QA performance, not simply proving that checks exist.

## Ground Truth Summary

The latest local run summary is written to `reports/generated_qa_summary.md`.

Detailed generated CSV outputs are written under `data/qa/evaluation/`, `data/qa/detections/`, and `data/raw/synthetic_corrupted/`. Those CSVs are ignored by git so the repository keeps source and summary artifacts without committing generated raw data.

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

The local pipeline compares z-score and IQR settings such as `z=2.0_iqr=1.5`, `z=2.5_iqr=2.0`, and `z=3.0_iqr=3.0`. The generated threshold comparison table is included in `reports/generated_qa_summary.md`.

## Selected Operating Threshold

The selected operating threshold is generated from the local run using overall F1 score, with recall and precision used as tie-breakers. The selected threshold should balance reporting accuracy and reviewer workload.

## Reviewer Tradeoff

Lower thresholds may catch more injected issues but create more false positives. Higher thresholds may reduce reviewer workload but risk allowing seeded reporting errors to remain undetected.

## Current Status

The evaluation framework and local pipeline are implemented. Run `python -m qa.run_local_qa_pipeline` to refresh ignored detailed CSV outputs and the committed summary report.
