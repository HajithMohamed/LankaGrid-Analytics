# Five-Year Historical Data Profiling Report (2020–2024)

## 1. Scope & Preprocessing Methodology

This profiling report assesses the statistical properties, data quality anomalies, physical unit integrity, and structural characteristics of the five-year authentic dataset (2020–2024) loaded into the **GridLens Data Warehouse**.

The profiling adheres directly to **Lecture 6 Data Preprocessing** principles:
1. **Missing Value Identification & Preservation**: Strict differentiation between physical zero ($0\text{ MW}$) and missing data (`NULL` / sentinels).
2. **Duplicate Detection & Elimination**: Natural key grain enforcement and multi-source collision avoidance.
3. **Noise & Outlier Detection**: Domain-specific physical boundary checks ($0 \le P \le P_{\text{installed}}$, $0 \le \text{Irradiance} \le 40\text{ MJ/m}^2/\text{day}$).
4. **Physical Unit Normalization**: Enforced SI conversion factors via conformed mapping tables (`ref.unit_conversion` and `etl.fn_convert_unit`).
5. **Cross-Source Reconciliation & Precedence**: Audited statistical digest priority over interim operational reports for billing and accounting figures.

---

## 2. Dataset Volumes & Profiling Statistics

| Source Category | Raw Record Count | Promoted DW Fact Count | Quarantined Count | Primary Warehouse Table | Audit Status |
|---|---|---|---|---|---|
| **CEB Statistical Digests (2020–2024)** | 49 tariff records | 49 fact rows | 0 rows | `dw.fact_electricity_sales` | Fully Reconciled |
| **NASA POWER Weather (2020–2024)** | 21,924 parameter records | 21,924 fact rows | 0 rows | `dw.fact_weather_daily` | 100% Continuity (`time_standard: LST`) |
| **PUCSL Sub-Daily Dispatch (March 2024)** | 107,136 interval readings | 107,115 fact rows | 21 rows | `dw.fact_dispatch_interval` | 31 Days Complete; Slot 96 Repaired |
| **PUCSL Daily Report (Dec 2024)** | 52 plant records | 52 fact rows | 0 rows | `dw.fact_generation_period` | Operational Baseline |

---

## 3. Negative Barge Readings: Investigation & Domain Handling

Across all 31 daily sheets of March 2024 (107,136 numeric readings), exactly **21 negative readings** were detected:
- **Entity**: Colombo Port `'Barge'` (floating oil-fired thermal station).
- **Recorded Values**: $-1.0\text{ MW}$ and $-2.0\text{ MW}$.
- **Occurrences**: Scattered across night-time and idle intervals when the barge generators were offline.

### 3.1 Domain Engineering Assessment
In electric power plant operations, an offline thermal generator does not produce electricity; instead, its auxiliary systems (lube oil heaters, boiler circulating pumps, control room equipment, navigation beacons) draw electrical power from the grid via the plant step-up/step-down transformer. This reverse power flow constitutes **auxiliary service import load**, not generation.

### 3.2 Warehouse Architecture Decision
1. **Preserve Provenance**: The raw negative values are faithfully preserved in `staging.stg_dispatch_observation` (`parsed_power_mw = -1.0` or `-2.0`).
2. **Quarantine Isolation**: In `etl.sp_validate_staged_dispatch`, rows with active power $< 0$ are quarantined into `staging.stg_quarantined_record` under rule code `DQ_GEN_NEGATIVE_OUTPUT` and logged in `audit.data_quality_issue`.
3. **Metric Integrity**: Because `dw.fact_dispatch_interval.active_power_mw` measures gross plant generation output, admitting negative auxiliary import without dedicated auxiliary meters would distort plant availability and capacity factor calculations.
4. **Result**: Exactly 21 rows quarantined; exactly $107,136 - 21 = 107,115$ valid generation facts promoted to `dw.fact_dispatch_interval_y2024`.

---

## 4. Cross-Source Aggregation & Reconciliation Analysis

### 4.1 PUCSL March 1, 2024 Dispatch Reconciliation (Published vs Telemetered)

On March 1, 2024 (Sheet `01.03`):
- **Published Daily Energy Total (Sheet Col 98, Row 39)**: **48,223.0 MWh**
- **Sum of Reporting Entity Published Energy (Rows 3..38, Col 98)**: **48,223.0 MWh** (Exact 100% agreement between summary row and constituent rows).
- **Sum of 15-Minute SCADA Telemetry ($\sum P_{15} \times 0.25\text{ h}$)**: **46,307.5 MWh** (Variance $\Delta = 1,915.5\text{ MWh}$ or $-3.97\%$).

#### Scope Difference Breakdown:
1. **Solar Aggregation (`Solar**`)**:
   - Published daily total: **2,379.7 MWh**
   - 15-minute transmission SCADA: **651.5 MWh**
   - Variance: $\mathbf{+1,728.2\text{ MWh}}$ ($90.2\%$ of total variance).
   - *Explanation*: The published daily solar figure includes embedded and rooftop solar PV (Net Metering, Net Accounting, Net Plus programs) metered on distribution feeders or estimated daily. The transmission SCADA telemetry records only utility-scale transmission-connected solar parks (e.g., Welikanda, Hambantota).
2. **Mini Hydro (`CEB/IPP Mini Hydro***`)**:
   - Published daily total: **1,896.8 MWh**
   - 15-minute SCADA: **1,594.0 MWh**
   - Variance: $\mathbf{+302.8\text{ MWh}}$ ($15.8\%$ of total variance).
   - *Explanation*: Non-telemetered run-of-river mini-hydro plants connected at 33 kV distribution level communicate daily bulk energy readings via telephone/logbook settlement rather than live 15-minute automated SCADA.
3. **Riemann Integration Sampling vs Revenue Metering**:
   - For thermal and large hydro plants, published energy derives from high-precision continuous revenue-grade integrating meters, whereas $\sum P_{15} \times 0.25$ represents a discrete Riemann sum sampling at instantaneous 15-minute intervals (e.g. Canyon: published $438.0\text{ MWh}$ vs derived $432.75\text{ MWh}$; West Coast: published $5,727.1\text{ MWh}$ vs derived $5,897.75\text{ MWh}$).
- **Conclusion**: The formula $E = P \times 0.25\text{ h}$ verifies internal mathematical consistency of discrete SCADA telemetry, but published daily totals reflect broader national physical grid coverage. Both are preserved with clear lineage.

### 4.2 CEB Five-Year Sales Reconciliation (2020–2024)

In CEB Annual Statistical Digests, retail consumer sales and bulk sales to the distribution franchisee (LECO) reconcile to published total sales within published integer rounding bounds:

| Calendar Year | Retail Sectors Sum (GWh) | LECO Bulk Supply (GWh) | Total Calculated (GWh) | Published Digest Total (GWh) | Rounding Variance ($\Delta$) | Status |
|---|---|---|---|---|---|---|
| **2020** | 12,682.0 | 1,605.0 | 14,287.0 | 14,286.0 | +1.0 GWh | Verified Reconciled |
| **2021** | 13,581.0 | 1,633.0 | 15,214.0 | 15,214.0 | 0.0 GWh | Exact Match |
| **2022** | 12,970.0 | 1,550.0 | 14,520.0 | 14,520.0 | 0.0 GWh | Exact Match |
| **2023** | 12,614.5 | 1,539.0 | 14,153.5 | 14,153.0 | +0.5 GWh | Verified Reconciled |
| **2024** | 13,565.5 | 1,625.0 | 15,190.5 | 15,191.0 | -0.5 GWh | Verified Reconciled |

All 5 years exhibit 100% accounting reconciliation within the published rounding precision ($\pm 1.0\text{ GWh}$).

---

## 5. Physical Unit Normalization & Solar Irradiance Recalculation

### 5.1 Solar Irradiance Canonical Conversion
The NASA POWER API reports daily solar shortwave downward irradiance (`ALLSKY_SFC_SW_DWN`) in $\text{kWh/m}^2/\text{day}$.
The canonical SI unit in `ref.unit` is $\text{MJ/m}^2/\text{day}$ ($1\text{ kWh} = 3.6\text{ MJ}$).

Recalculated 5-year solar irradiance profile across observation nodes:
- **Victoria Hydro Catchment (Central Highlands)**:
  - 2020: Min $4.89$, **Mean 19.25**, Max $27.29\text{ MJ/m}^2/\text{day}$ (aligned from erroneous earlier draft of 17.82).
  - 2021: Min $3.84$, **Mean 18.84**, Max $26.31\text{ MJ/m}^2/\text{day}$.
  - 2022: Min $1.55$, **Mean 18.39**, Max $25.97\text{ MJ/m}^2/\text{day}$.
  - 2023: Min $7.80$, **Mean 18.69**, Max $26.92\text{ MJ/m}^2/\text{day}$.
  - 2024: Min $1.59$, **Mean 18.67**, Max $27.31\text{ MJ/m}^2/\text{day}$.
- **Mannar Wind Corridor (Northern Coast)**:
  - 2020: Min $2.66$, **Mean 19.72**, Max $25.90\text{ MJ/m}^2/\text{day}$.
  - 2021: Min $2.43$, **Mean 19.42**, Max $26.01\text{ MJ/m}^2/\text{day}$.
  - 2022: Min $3.67$, **Mean 19.17**, Max $25.83\text{ MJ/m}^2/\text{day}$.
  - 2023: Min $3.70$, **Mean 19.48**, Max $26.11\text{ MJ/m}^2/\text{day}$.
  - 2024: Min $2.24$, **Mean 19.16**, Max $26.16\text{ MJ/m}^2/\text{day}$.

### 5.2 Time Standard Alignment (`LST`)
NASA POWER data specifies `time_standard: LST` (Local Solar Time). The warehouse records `'LST'` in `dw.fact_weather_daily.time_standard`, maintaining complete metadata fidelity without artificially coercing to SLST (UTC+05:30).

---

## 6. Dispatch Slot 96 & Date Key Resolution

### 6.1 Defect Analysis
In previous iterations, the dispatch parser represented interval slot 96 (ending at 24:00 SLST) as midnight of the following day (`00:00:00+05:30` on $D+1$). Because staging discarded the reporting date and slot number, the stored procedure converted `parsed_timestamp::DATE`, shifting March 1 slot 96 to March 2, and March 31 slot 96 to April 1.

### 6.2 Solution & Migration 020
1. Staging table `staging.stg_dispatch_observation` was augmented with:
   - `reporting_date DATE NOT NULL`
   - `interval_slot_number SMALLINT NOT NULL`
2. Stored procedure `etl.sp_load_dispatch_interval` was updated to resolve `v_date_key` directly from `rec.reporting_date` and `v_interval_key` from `rec.interval_slot_number`.
3. Migration 020 executed an auditable DML repair on existing facts in `dw.fact_dispatch_interval`, reassigning misplaced slot 96 records from $D+1$ back to $D$.
4. **Verification**: Full 31-day load confirms:
   - March 1 has exactly 96 intervals.
   - March 2 has exactly 96 intervals.
   - March 31 has exactly 96 intervals.
   - Exactly **0 facts** exist for `date_key = 20240401`.
