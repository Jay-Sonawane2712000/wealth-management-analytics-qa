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

-- Deterministic hard-rule detections on corrupted synthetic performance data.
-- This view mirrors the local pandas hard-rule detector and is intended for
-- future Snowflake execution. Statistical anomaly detection and scoring against
-- ground truth come later.
CREATE OR REPLACE VIEW QA.HARD_RULE_DETECTION_RESULTS AS
WITH duplicate_account_month AS (
    SELECT
        ACCOUNT_ID,
        MONTH_END_DATE
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED
    GROUP BY ACCOUNT_ID, MONTH_END_DATE
    HAVING COUNT(*) > 1
),
raw_detections AS (
    SELECT
        'negative_ending_aum' AS rule_name,
        'hard_rule' AS detection_family,
        PERFORMANCE_ID,
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE,
        'ending_aum' AS field_name,
        TO_VARCHAR(ENDING_AUM) AS observed_value,
        'ending_aum >= 0' AS expected_condition,
        'high' AS severity,
        'Ending AUM is negative.' AS explanation,
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS detected_at
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED
    WHERE ENDING_AUM < 0

    UNION ALL

    SELECT
        'negative_revenue',
        'hard_rule',
        PERFORMANCE_ID,
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE,
        'revenue',
        TO_VARCHAR(REVENUE),
        'revenue >= 0',
        'high',
        'Revenue is negative.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED
    WHERE REVENUE < 0

    UNION ALL

    SELECT
        'invalid_fee_rate_high',
        'hard_rule',
        PERFORMANCE_ID,
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE,
        'fee_rate',
        TO_VARCHAR(FEE_RATE),
        'fee_rate <= 0.0150',
        'high',
        'Fee rate is above the expected advisory range.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED
    WHERE FEE_RATE > 0.0150

    UNION ALL

    SELECT
        'invalid_fee_rate_low',
        'hard_rule',
        PERFORMANCE_ID,
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE,
        'fee_rate',
        TO_VARCHAR(FEE_RATE),
        'fee_rate >= 0.0025',
        'medium',
        'Fee rate is below the expected advisory range.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED
    WHERE FEE_RATE < 0.0025

    UNION ALL

    SELECT
        'duplicate_account_month',
        'hard_rule',
        p.PERFORMANCE_ID,
        p.ACCOUNT_ID,
        p.ADVISOR_ID,
        p.BRANCH_ID,
        p.FIRM_CRD_NUMBER,
        p.MONTH_END_DATE,
        'account_id,month_end_date',
        p.ACCOUNT_ID || '|' || TO_VARCHAR(p.MONTH_END_DATE),
        'one row per account_id and month_end_date',
        'high',
        'Multiple performance rows exist for the same account-month.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED p
    JOIN duplicate_account_month d
        ON p.ACCOUNT_ID = d.ACCOUNT_ID
        AND p.MONTH_END_DATE = d.MONTH_END_DATE

    UNION ALL

    SELECT
        'revenue_on_closed_account',
        'hard_rule',
        p.PERFORMANCE_ID,
        p.ACCOUNT_ID,
        p.ADVISOR_ID,
        p.BRANCH_ID,
        p.FIRM_CRD_NUMBER,
        p.MONTH_END_DATE,
        'revenue',
        TO_VARCHAR(p.REVENUE),
        'revenue = 0 when account_status = closed',
        'medium',
        'Closed account has positive revenue.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED p
    JOIN RAW.SYNTHETIC_ACCOUNTS a
        ON p.ACCOUNT_ID = a.ACCOUNT_ID
    WHERE a.ACCOUNT_STATUS = 'closed'
        AND p.REVENUE > 0

    UNION ALL

    SELECT
        'missing_account_reference',
        'hard_rule',
        p.PERFORMANCE_ID,
        p.ACCOUNT_ID,
        p.ADVISOR_ID,
        p.BRANCH_ID,
        p.FIRM_CRD_NUMBER,
        p.MONTH_END_DATE,
        'account_id',
        TO_VARCHAR(p.ACCOUNT_ID),
        'account_id exists in synthetic_accounts',
        'high',
        'Performance row references a missing account.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED p
    LEFT JOIN RAW.SYNTHETIC_ACCOUNTS a
        ON p.ACCOUNT_ID = a.ACCOUNT_ID
    WHERE p.ACCOUNT_ID IS NOT NULL
        AND a.ACCOUNT_ID IS NULL

    UNION ALL

    SELECT
        'missing_advisor_reference',
        'hard_rule',
        p.PERFORMANCE_ID,
        p.ACCOUNT_ID,
        p.ADVISOR_ID,
        p.BRANCH_ID,
        p.FIRM_CRD_NUMBER,
        p.MONTH_END_DATE,
        'advisor_id',
        TO_VARCHAR(p.ADVISOR_ID),
        'advisor_id exists in synthetic_advisors',
        'high',
        'Performance row references a missing advisor.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED p
    LEFT JOIN RAW.SYNTHETIC_ADVISORS a
        ON p.ADVISOR_ID = a.ADVISOR_ID
    WHERE p.ADVISOR_ID IS NOT NULL
        AND a.ADVISOR_ID IS NULL

    UNION ALL

    SELECT
        'missing_branch_reference',
        'hard_rule',
        p.PERFORMANCE_ID,
        p.ACCOUNT_ID,
        p.ADVISOR_ID,
        p.BRANCH_ID,
        p.FIRM_CRD_NUMBER,
        p.MONTH_END_DATE,
        'branch_id',
        TO_VARCHAR(p.BRANCH_ID),
        'branch_id exists in synthetic_branches',
        'high',
        'Performance row references a missing branch.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED p
    LEFT JOIN RAW.SYNTHETIC_BRANCHES b
        ON p.BRANCH_ID = b.BRANCH_ID
    WHERE p.BRANCH_ID IS NOT NULL
        AND b.BRANCH_ID IS NULL

    UNION ALL

    SELECT
        'null_key_fields',
        'hard_rule',
        PERFORMANCE_ID,
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE,
        'key_fields',
        'NULL',
        'key fields are not null',
        'high',
        'One or more required key fields are null.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED
    WHERE PERFORMANCE_ID IS NULL
        OR ACCOUNT_ID IS NULL
        OR ADVISOR_ID IS NULL
        OR BRANCH_ID IS NULL
        OR FIRM_CRD_NUMBER IS NULL
        OR MONTH_END_DATE IS NULL
)
SELECT
    'SQL-HARD-' || LPAD(ROW_NUMBER() OVER (ORDER BY rule_name, performance_id)::VARCHAR, 6, '0') AS detection_id,
    rule_name,
    detection_family,
    performance_id,
    account_id,
    advisor_id,
    branch_id,
    firm_crd_number,
    month_end_date,
    field_name,
    observed_value,
    expected_condition,
    severity,
    explanation,
    detected_at
FROM raw_detections;

-- Warehouse-side statistical anomaly detection placeholder/implementation.
-- Python detection is used for local development and testing. This view shows
-- how AUM growth and revenue anomaly logic can be represented in Snowflake
-- with window functions. Final evaluation against ground truth happens later.
CREATE OR REPLACE VIEW QA.STATISTICAL_DETECTION_RESULTS AS
WITH monthly_account_metrics AS (
    SELECT
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE,
        SUM(ENDING_AUM) AS ending_aum,
        SUM(REVENUE) AS revenue
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE_CORRUPTED
    GROUP BY
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE
),
aum_growth AS (
    SELECT
        *,
        LAG(ending_aum) OVER (
            PARTITION BY ADVISOR_ID
            ORDER BY MONTH_END_DATE
        ) AS previous_month_ending_aum,
        (ending_aum - LAG(ending_aum) OVER (
            PARTITION BY ADVISOR_ID
            ORDER BY MONTH_END_DATE
        )) / NULLIF(LAG(ending_aum) OVER (
            PARTITION BY ADVISOR_ID
            ORDER BY MONTH_END_DATE
        ), 0) AS mom_aum_growth
    FROM monthly_account_metrics
),
scored AS (
    SELECT
        *,
        AVG(mom_aum_growth) OVER (PARTITION BY ADVISOR_ID) AS avg_aum_growth,
        STDDEV_POP(mom_aum_growth) OVER (PARTITION BY ADVISOR_ID) AS stddev_aum_growth,
        AVG(revenue) OVER (PARTITION BY ADVISOR_ID) AS avg_revenue,
        STDDEV_POP(revenue) OVER (PARTITION BY ADVISOR_ID) AS stddev_revenue
    FROM aum_growth
),
raw_statistical_detections AS (
    SELECT
        'zscore_aum_growth_anomaly' AS rule_name,
        'statistical_rule' AS detection_family,
        NULL AS performance_id,
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE,
        'mom_aum_growth' AS field_name,
        TO_VARCHAR(mom_aum_growth) AS observed_value,
        'absolute z-score <= configured threshold' AS expected_condition,
        'medium' AS severity,
        'AUM growth z-score exceeded the configured threshold.' AS explanation,
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS detected_at
    FROM scored
    WHERE stddev_aum_growth IS NOT NULL
        AND stddev_aum_growth > 0
        AND ABS((mom_aum_growth - avg_aum_growth) / stddev_aum_growth) > 3.0

    UNION ALL

    SELECT
        'zscore_revenue_anomaly',
        'statistical_rule',
        NULL,
        ACCOUNT_ID,
        ADVISOR_ID,
        BRANCH_ID,
        FIRM_CRD_NUMBER,
        MONTH_END_DATE,
        'revenue',
        TO_VARCHAR(revenue),
        'absolute z-score <= configured threshold',
        'medium',
        'Revenue z-score exceeded the configured threshold.',
        CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
    FROM scored
    WHERE stddev_revenue IS NOT NULL
        AND stddev_revenue > 0
        AND ABS((revenue - avg_revenue) / stddev_revenue) > 3.0
)
SELECT
    'SQL-STAT-' || LPAD(ROW_NUMBER() OVER (ORDER BY rule_name, advisor_id, month_end_date)::VARCHAR, 6, '0') AS detection_id,
    rule_name,
    detection_family,
    performance_id,
    account_id,
    advisor_id,
    branch_id,
    firm_crd_number,
    month_end_date,
    field_name,
    observed_value,
    expected_condition,
    severity,
    explanation,
    detected_at
FROM raw_statistical_detections;
