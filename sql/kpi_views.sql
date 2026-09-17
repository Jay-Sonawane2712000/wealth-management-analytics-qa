-- Clean baseline KPI views for wealth-management reporting.
-- These views combine real public firm metadata from RAW.SEC_ADV_FIRMS with
-- synthetic private-style branch, advisor, account, and monthly performance
-- records from RAW.SYNTHETIC_* tables.
-- No injected-error QA or anomaly detection is implemented here.

-- Advisor-level monthly performance rollup.
CREATE OR REPLACE VIEW ANALYTICS.ADVISOR_MONTHLY_KPIS AS
SELECT
    p.MONTH_END_DATE AS month_end_date,
    p.FIRM_CRD_NUMBER AS firm_crd_number,
    f.FIRM_NAME AS firm_name,
    p.BRANCH_ID AS branch_id,
    b.BRANCH_NAME AS branch_name,
    p.ADVISOR_ID AS advisor_id,
    a.ADVISOR_NAME AS advisor_name,
    a.PRIMARY_CLIENT_SEGMENT AS primary_client_segment,
    COUNT(DISTINCT p.ACCOUNT_ID) AS account_count,
    COUNT(DISTINCT CASE WHEN acct.ACCOUNT_STATUS = 'active' THEN p.ACCOUNT_ID END) AS active_account_count,
    SUM(p.BEGINNING_AUM) AS beginning_aum,
    SUM(p.ENDING_AUM) AS ending_aum,
    SUM(p.NET_NEW_ASSETS) AS net_new_assets,
    SUM(p.REVENUE) AS revenue,
    AVG(p.FEE_RATE) AS avg_fee_rate,
    (SUM(p.ENDING_AUM) - SUM(p.BEGINNING_AUM)) / NULLIF(SUM(p.BEGINNING_AUM), 0) AS aum_growth_rate,
    SUM(p.REVENUE) / NULLIF(COUNT(DISTINCT p.ACCOUNT_ID), 0) AS revenue_per_account
FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE p
JOIN RAW.SYNTHETIC_ACCOUNTS acct
    ON p.ACCOUNT_ID = acct.ACCOUNT_ID
JOIN RAW.SYNTHETIC_ADVISORS a
    ON p.ADVISOR_ID = a.ADVISOR_ID
JOIN RAW.SYNTHETIC_BRANCHES b
    ON p.BRANCH_ID = b.BRANCH_ID
LEFT JOIN RAW.SEC_ADV_FIRMS f
    ON p.FIRM_CRD_NUMBER = f.FIRM_CRD_NUMBER
GROUP BY
    p.MONTH_END_DATE,
    p.FIRM_CRD_NUMBER,
    f.FIRM_NAME,
    p.BRANCH_ID,
    b.BRANCH_NAME,
    p.ADVISOR_ID,
    a.ADVISOR_NAME,
    a.PRIMARY_CLIENT_SEGMENT;

-- Branch-level monthly performance rollup.
CREATE OR REPLACE VIEW ANALYTICS.BRANCH_MONTHLY_KPIS AS
SELECT
    p.MONTH_END_DATE AS month_end_date,
    p.FIRM_CRD_NUMBER AS firm_crd_number,
    f.FIRM_NAME AS firm_name,
    p.BRANCH_ID AS branch_id,
    b.BRANCH_NAME AS branch_name,
    b.BRANCH_REGION AS branch_region,
    COUNT(DISTINCT p.ADVISOR_ID) AS advisor_count,
    COUNT(DISTINCT p.ACCOUNT_ID) AS account_count,
    SUM(p.BEGINNING_AUM) AS beginning_aum,
    SUM(p.ENDING_AUM) AS ending_aum,
    SUM(p.NET_NEW_ASSETS) AS net_new_assets,
    SUM(p.REVENUE) AS revenue,
    AVG(p.FEE_RATE) AS avg_fee_rate,
    (SUM(p.ENDING_AUM) - SUM(p.BEGINNING_AUM)) / NULLIF(SUM(p.BEGINNING_AUM), 0) AS aum_growth_rate,
    SUM(p.REVENUE) / NULLIF(COUNT(DISTINCT p.ADVISOR_ID), 0) AS revenue_per_advisor
FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE p
JOIN RAW.SYNTHETIC_ACCOUNTS acct
    ON p.ACCOUNT_ID = acct.ACCOUNT_ID
JOIN RAW.SYNTHETIC_ADVISORS a
    ON p.ADVISOR_ID = a.ADVISOR_ID
JOIN RAW.SYNTHETIC_BRANCHES b
    ON p.BRANCH_ID = b.BRANCH_ID
LEFT JOIN RAW.SEC_ADV_FIRMS f
    ON p.FIRM_CRD_NUMBER = f.FIRM_CRD_NUMBER
GROUP BY
    p.MONTH_END_DATE,
    p.FIRM_CRD_NUMBER,
    f.FIRM_NAME,
    p.BRANCH_ID,
    b.BRANCH_NAME,
    b.BRANCH_REGION;

-- Firm-level monthly performance rollup combining real firm metadata with
-- synthetic operating performance.
CREATE OR REPLACE VIEW ANALYTICS.FIRM_MONTHLY_KPIS AS
SELECT
    p.MONTH_END_DATE AS month_end_date,
    p.FIRM_CRD_NUMBER AS firm_crd_number,
    f.FIRM_NAME AS firm_name,
    f.REGISTRATION_STATE AS registration_state,
    f.REGULATORY_AUM AS regulatory_aum,
    COUNT(DISTINCT p.ADVISOR_ID) AS advisor_count,
    COUNT(DISTINCT p.BRANCH_ID) AS branch_count,
    COUNT(DISTINCT p.ACCOUNT_ID) AS account_count,
    SUM(p.BEGINNING_AUM) AS beginning_aum,
    SUM(p.ENDING_AUM) AS ending_aum,
    SUM(p.NET_NEW_ASSETS) AS net_new_assets,
    SUM(p.REVENUE) AS revenue,
    AVG(p.FEE_RATE) AS avg_fee_rate,
    (SUM(p.ENDING_AUM) - SUM(p.BEGINNING_AUM)) / NULLIF(SUM(p.BEGINNING_AUM), 0) AS aum_growth_rate,
    SUM(p.ENDING_AUM) / NULLIF(f.REGULATORY_AUM, 0) AS synthetic_to_regulatory_aum_ratio
FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE p
JOIN RAW.SYNTHETIC_ACCOUNTS acct
    ON p.ACCOUNT_ID = acct.ACCOUNT_ID
JOIN RAW.SYNTHETIC_ADVISORS a
    ON p.ADVISOR_ID = a.ADVISOR_ID
JOIN RAW.SYNTHETIC_BRANCHES b
    ON p.BRANCH_ID = b.BRANCH_ID
LEFT JOIN RAW.SEC_ADV_FIRMS f
    ON p.FIRM_CRD_NUMBER = f.FIRM_CRD_NUMBER
GROUP BY
    p.MONTH_END_DATE,
    p.FIRM_CRD_NUMBER,
    f.FIRM_NAME,
    f.REGISTRATION_STATE,
    f.REGULATORY_AUM;

-- Stakeholder-ready monthly summary. QA has not been run yet, so the status is
-- intentionally explicit rather than implying completed anomaly detection.
CREATE OR REPLACE VIEW REPORTING.EXECUTIVE_MONTHLY_SUMMARY AS
WITH branch_revenue AS (
    SELECT
        p.MONTH_END_DATE,
        p.BRANCH_ID,
        b.BRANCH_NAME,
        SUM(p.REVENUE) AS branch_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY p.MONTH_END_DATE
            ORDER BY SUM(p.REVENUE) DESC, p.BRANCH_ID
        ) AS revenue_rank
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE p
    JOIN RAW.SYNTHETIC_BRANCHES b
        ON p.BRANCH_ID = b.BRANCH_ID
    GROUP BY
        p.MONTH_END_DATE,
        p.BRANCH_ID,
        b.BRANCH_NAME
),
monthly_summary AS (
    SELECT
        p.MONTH_END_DATE AS month_end_date,
        COUNT(DISTINCT p.FIRM_CRD_NUMBER) AS total_firms,
        COUNT(DISTINCT p.BRANCH_ID) AS total_branches,
        COUNT(DISTINCT p.ADVISOR_ID) AS total_advisors,
        COUNT(DISTINCT p.ACCOUNT_ID) AS total_accounts,
        SUM(p.BEGINNING_AUM) AS total_beginning_aum,
        SUM(p.ENDING_AUM) AS total_ending_aum,
        SUM(p.NET_NEW_ASSETS) AS total_net_new_assets,
        SUM(p.REVENUE) AS total_revenue,
        (SUM(p.ENDING_AUM) - SUM(p.BEGINNING_AUM)) / NULLIF(SUM(p.BEGINNING_AUM), 0) AS portfolio_aum_growth_rate,
        AVG(p.FEE_RATE) AS average_fee_rate
    FROM RAW.SYNTHETIC_MONTHLY_PERFORMANCE p
    GROUP BY p.MONTH_END_DATE
)
SELECT
    s.month_end_date,
    s.total_firms,
    s.total_branches,
    s.total_advisors,
    s.total_accounts,
    s.total_beginning_aum,
    s.total_ending_aum,
    s.total_net_new_assets,
    s.total_revenue,
    s.portfolio_aum_growth_rate,
    s.average_fee_rate,
    br.BRANCH_ID AS top_revenue_branch_id,
    br.BRANCH_NAME AS top_revenue_branch_name,
    'QA_NOT_RUN_YET' AS qa_status_placeholder
FROM monthly_summary s
LEFT JOIN branch_revenue br
    ON s.month_end_date = br.MONTH_END_DATE
    AND br.revenue_rank = 1;
