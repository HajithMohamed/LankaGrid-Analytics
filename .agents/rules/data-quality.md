---
trigger: always_on
description: Data quality standards, anomaly detection, noise, and Lecture 6 preprocessing rules
---
# Data Quality & Preprocessing Rules

## Core Principles
1. **Never Fabricate Data**:
   - Fabricating measurements, proxy dates, or grid readings is strictly prohibited.
   - If historical records are missing from official sources, document the gap explicitly.
2. **Lecture 6 Data Preprocessing Compliance**:
   - **Missing Values**: Identify systematically. Classify as Missing Completely at Random (MCAR), Missing at Random (MAR), or Not at Random (MNAR). Choose domain-justified handling (explicit sentinel, linear interpolation for short gaps with flags, or exclusion from specific aggregations).
   - **Duplicate Detection**: Identify exact duplicates and fuzzy duplicates (e.g., slight station name spelling variations such as "Lakvijaya" vs "Lakvijaya Coal").
   - **Noise & Outlier Detection**: Apply domain boundary checks (e.g., generation cannot exceed station rated nameplate capacity $P > P_{\text{installed}}$; negative generation only for pumped storage/auxiliary consumption).
   - **Inconsistency Resolution**: Check that sum of individual unit dispatches equals total station dispatch $\pm \epsilon$. Check that system gross generation minus transmission/distribution losses equals net consumption.
   - **Unit & Timestamp Normalization**: Standardize all power units to MW and energy to MWh. Standardize timestamps to ISO 8601 with Sri Lanka offset: `YYYY-MM-DDTHH:MM:SS+05:30`.
   - **Source Conflict Handling**: When CEB statistical digest and PUCSL daily reports differ, preserve both in staging, calculate variance, and document precedence hierarchy (e.g. PUCSL dispatch for operational 15-minute curves; CEB annual audited statistics for finalized billing reconciliations).

## Automated Validation Gates
- Every ETL batch must run quality assertions:
  - Row count consistency check.
  - Primary key uniqueness check.
  - Foreign key referential integrity check.
  - Domain range checks ($MW \ge 0$, Solar Irradiance $\ge 0$).
  - Temporal continuity checks (no unexplained multi-hour gaps in 15-minute dispatch).
