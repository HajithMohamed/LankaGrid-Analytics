---
name: data-preprocessing
description: >-
  Provides procedures for Lecture 6 data preprocessing: missing value detection/imputation,
  duplicate detection, noise and outlier filtering, unit and timestamp normalization, and source conflict resolution.
  Use when cleaning, parsing, or transforming raw electricity datasets into staging data.
---

# Data Preprocessing Skill

## When to Use This Skill
Use this skill when developing or debugging preprocessing routines in `src/preprocessing/` for raw tabular, PDF, or API datasets according to Data Warehousing Lecture 6 standards.

## Preprocessing Procedures

### 1. Missing Value Detection & Treatment
1. Detect missing values across all columns (`NaN`, empty strings, whitespace, sentinels like `-`, `N/A`, `9999`).
2. Categorize the missing mechanism:
   - **MCAR** (Missing Completely at Random): Unsystematic transmission glitch.
   - **MAR** (Missing at Random): Specific non-dispatchable plants omitting daytime-only records.
   - **MNAR** (Missing Not at Random): Generator failure causing monitoring equipment shutdown.
3. NEVER replace missing values with `0`. Zero denotes operational zero output (e.g. solar at night or plant offline).
4. Treatment strategy:
   - Fact measures: Preserve `NULL` with a data quality indicator column (`is_imputed = FALSE`).
   - Time-series dispatch: For single isolated missing 15-minute readings, apply linear interpolation only when explicitly marked with `imputation_flag = TRUE`.

### 2. Duplicate Detection
1. **Exact Duplicates**: Identify rows identical across all columns and deduplicate while logging occurrence count.
2. **Key / Semantic Duplicates**: Detect multiple records for the same plant and timestamp. Resolve by source authority hierarchy and log conflict.
3. **Fuzzy Entity Matching**: Standardize power plant naming variants (e.g. "Kelanitissa Combined Cycle" vs "KCCP" vs "Kelanitissa CCGT") using canonical lookup tables in `src/common/entity_mapping.py`.

### 3. Noise & Outlier Detection
1. Physical boundary validation:
   - $0 \le P_{\text{actual}} \le P_{\text{rated}} \times 1.05$ (allowing max 5% spinning overload).
   - Frequency: $49.0\text{ Hz} \le f \le 51.0\text{ Hz}$.
   - System Total Demand: Between $1{,}000\text{ MW}$ (trough night) and $3{,}200\text{ MW}$ (historical national peak).
2. Statistical outlier detection:
   - Compute Z-score or Interquartile Range ($IQR = Q_3 - Q_1$).
   - Flag values outside $[Q_1 - 1.5 \times IQR, Q_3 + 1.5 \times IQR]$ as statistical outliers for engineering review.

### 4. Unit & Timestamp Normalization
1. Parse all datetime strings into Python `datetime` objects with timezone `Asia/Colombo` (`UTC+05:30`).
2. Normalize power measurements to **MW** (Megawatts) with 3 decimal precision.
3. Normalize energy measurements to **MWh** (Megawatt-hours). Convert GWh to MWh ($1\text{ GWh} = 1{,}000\text{ MWh}$).
4. Verify conservation of energy: 15-minute generation ($MWh = MW \times 0.25$).

### 5. Source Conflict Handling
1. Compare overlapping data from CEB Statistical Digest vs PUCSL Daily Generation reports.
2. In case of discrepancy:
   - Retain both values in audit staging with source tag.
   - For operational dispatch (15-min), PUCSL generation reports are authoritative.
   - For annual audited billing and provincial sales, CEB Statistical Digest is authoritative.

## Expected Outputs
- Cleaned DataFrame or Parquet/CSV in `data/staging/`
- Data quality profiling log detailing counts of missing, duplicate, and outlier records
- Quarantine table of rejected unparseable rows

## Verification Steps
1. Run automated preprocessing unit tests: `pytest tests/unit/test_preprocessing.py`.
2. Assert zero uncaught `NaN`s in primary business keys.
3. Check that maximum recorded plant output does not exceed rated capacity.
