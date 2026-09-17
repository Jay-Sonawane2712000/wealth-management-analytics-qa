-- Snowflake schema foundation for the wealth-management analytics QA project.
-- Run this script only after a Snowflake account, role, and warehouse strategy
-- are ready. Credentials must stay in a local .env file and out of git.

CREATE WAREHOUSE IF NOT EXISTS analytics_wh
    WITH WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;

CREATE DATABASE IF NOT EXISTS WEALTH_ANALYTICS;

USE DATABASE WEALTH_ANALYTICS;

CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS CLEAN;
CREATE SCHEMA IF NOT EXISTS ANALYTICS;
CREATE SCHEMA IF NOT EXISTS REPORTING;
CREATE SCHEMA IF NOT EXISTS QA;

-- RAW.SEC_ADV_FIRMS stores real public SEC/IAPD investment adviser firm data.
-- Future RAW.SYNTHETIC_* tables must remain separate from this public regulatory
-- layer so governance, lineage, and interpretation stay clear.
CREATE TABLE IF NOT EXISTS RAW.SEC_ADV_FIRMS (
    FIRM_CRD_NUMBER VARCHAR,
    FIRM_NAME VARCHAR,
    SEC_NUMBER VARCHAR,
    REGISTRATION_STATUS VARCHAR,
    REGISTRATION_STATE VARCHAR,
    MAIN_OFFICE_CITY VARCHAR,
    MAIN_OFFICE_STATE VARCHAR,
    MAIN_OFFICE_ZIP VARCHAR,
    REGULATORY_AUM NUMBER(18,2),
    EMPLOYEE_COUNT NUMBER,
    BRANCH_COUNT NUMBER,
    SOURCE_TYPE VARCHAR,
    SOURCE_FILE VARCHAR,
    INGESTED_AT TIMESTAMP_NTZ
);

-- Planned future RAW tables:
-- RAW.SYNTHETIC_ADVISORS: generated private-style advisor records.
-- RAW.SYNTHETIC_ACCOUNTS: generated private-style account records.
-- RAW.SYNTHETIC_MONTHLY_PERFORMANCE: generated private-style performance records.

-- Planned future QA tables:
-- QA.SEEDED_ERROR_LABELS: ground-truth labels for injected anomalies.
-- QA.DETECTED_ANOMALIES: rule and statistical anomaly detection output.
