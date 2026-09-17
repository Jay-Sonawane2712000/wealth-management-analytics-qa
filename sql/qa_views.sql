-- Baseline QA reporting views.
-- These views describe clean baseline data health before intentional error
-- injection. They do not implement final anomaly detection, seeded-error
-- precision/recall evaluation, or reviewer workflow logic.

CREATE OR REPLACE VIEW QA.BASELINE_DATA_HEALTH_SUMMARY AS
SELECT
    'synthetic branch row count' AS check_name,
    COUNT(*) AS issue_count,
    'INFO' AS status
FROM RAW.SYNTHETIC_BRANCHES

UNION ALL

SELECT
    'synthetic advisor row count' AS check_name,
    COUNT(*) AS issue_count,
    'INFO' AS status
FROM RAW.SYNTHETIC_ADVISORS

UNION ALL

SELECT
    'synthetic account row count' AS check_name,
    COUNT(*) AS issue_count,
    'INFO' AS status
FROM RAW.SYNTHETIC_ACCOUNTS

UNION ALL

SELECT
    'synthetic monthly performance row count' AS check_name,
    COUNT(*) AS issue_count,
    'INFO' AS status
FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE

UNION ALL

SELECT
    'negative ending AUM count' AS check_name,
    COUNT_IF(ENDING_AUM < 0) AS issue_count,
    CASE WHEN COUNT_IF(ENDING_AUM < 0) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE

UNION ALL

SELECT
    'negative revenue count' AS check_name,
    COUNT_IF(REVENUE < 0) AS issue_count,
    CASE WHEN COUNT_IF(REVENUE < 0) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE

UNION ALL

SELECT
    'invalid fee rate count' AS check_name,
    COUNT_IF(FEE_RATE < 0.0025 OR FEE_RATE > 0.0150) AS issue_count,
    CASE WHEN COUNT_IF(FEE_RATE < 0.0025 OR FEE_RATE > 0.0150) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE;
