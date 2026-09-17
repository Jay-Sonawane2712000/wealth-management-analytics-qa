-- Snowflake schema foundation for the wealth-management analytics QA project.
-- Connections and deployment are intentionally deferred to later phases.

-- Optional warehouse example:
-- CREATE WAREHOUSE analytics_wh WITH WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE;

CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS CLEAN;
CREATE SCHEMA IF NOT EXISTS ANALYTICS;
CREATE SCHEMA IF NOT EXISTS REPORTING;
CREATE SCHEMA IF NOT EXISTS QA;

-- Planned RAW tables:
-- RAW.SEC_ADV_FIRMS: real public SEC/IAPD adviser firm data.
-- RAW.SYNTHETIC_ADVISORS: generated private-style advisor records.
-- RAW.SYNTHETIC_ACCOUNTS: generated private-style account records.
-- RAW.SYNTHETIC_MONTHLY_PERFORMANCE: generated private-style performance records.

-- Planned QA tables:
-- QA.SEEDED_ERROR_LABELS: ground-truth labels for injected anomalies.
-- QA.DETECTED_ANOMALIES: rule and statistical anomaly detection output.
