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
| **CEB Statistical Digests (2020–2024)** | 44 tariff records | 44 fact rows | 0 rows | `dw.fact_electricity_sales` | Fully Reconciled |
| **NASA POWER Weather (2020–2024)** | 21,924 parameter records | 21,924 fact rows | 0 rows | `dw.fact_weather_daily` | 100% Continuity |
| **PUCSL Sub-Daily Dispatch (March 2024)** | 10,365 interval entries | 10,365 fact rows | 0 rows | `dw.fact_dispatch_interval` | Conservation of Energy Verified |
| **PUCSL Daily Report (Dec 2024)** | 52 plant records | 52 fact rows | 0 rows | `dw.fact_generation_period` | Verified |

---

## 3. Missing Value Analysis & Sentinel Handling

### 3.1 Domain Physics: Zero vs Missing

A critical flaw in naive grid analytics is replacing missing readings with zero or vice-versa. In electric power engineering:
- $0\text{ MW}$ indicates a completely shut down plant, a scheduled maintenance outage, or complete cloud curtailment on solar.
- Missing data (`NULL`) represents communication telemetry loss, RTU failure, or unrecorded historical intervals.
- Replacing missing values with zero artificially depresses calculated plant availability, capacity factors ($CF = \frac{E}{P_{\text{cap}} \times \Delta t}$), and peak load metrics.

### 3.2 NASA POWER Fill Values

- **Sentinel Code**: `-999.0`
- **Warehouse Rule**: Whenever NASA returns `-999.0`, the ETL pipeline:
  1. Sets `is_missing = TRUE`.
  2. Stores `missing_value_code = '-999.0'`.
  3. Sets `standardized_value = NULL` and `original_reported_value = NULL`.
  4. Never allows a check violation where `is_missing = TRUE` and `standardized_value` is non-null.
- **Observed 5-Year Frequency**: Across all 21,924 parameters from 2020 to 2024, NASA POWER demonstrated 100% data completeness for Victoria and Mannar nodes, with 0 missing sentinels encountered.

---

## 4. Physical Unit Conversion Evidence

### 4.1 Solar Irradiance Unit Conversion Verification

The NASA POWER API publishes daily horizontal solar irradiance (`ALLSKY_SFC_SW_DWN`) in native engineering units of:
$$\text{kWh/m}^2/\text{day}$$

The canonical physical unit specified in the GridLens dimensional warehouse (`ref.unit`) is:
$$\text{MJ/m}^2/\text{day}$$

Using the exact physical relationship $1\text{ kWh} = 3.6\text{ MJ}$:
$$\text{Value}_{\text{canonical}} = \text{Value}_{\text{NASA}} \times 3.6$$

**Dual-Unit Provenance Tracking**:
In `dw.fact_weather_daily`, every record explicitly preserves both the source-reported measurement and the canonical warehouse measurement:
- `original_reported_value`: e.g. $4.85\text{ kWh/m}^2/\text{day}$
- `original_unit_code`: `'kWh/m2/day'`
- `standardized_value`: $4.85 \times 3.6 = 17.46\text{ MJ/m}^2/\text{day}$
- `standardized_unit_code`: `'MJ/m2/day'`

### 4.2 Active Power (MW) vs Integrated Energy (MWh)

In sub-daily dispatch analytics (`dw.fact_dispatch_interval`):
- Active Power ($P$ in MW) is recorded for interval duration $\Delta t = 15\text{ minutes} = 0.25\text{ hours}$.
- Derived Energy ($E$ in MWh) is computed as:
$$E = P \times 0.25\text{ MWh}$$
- Database check constraint `ck_fact_dispatch_energy_consistency` enforces:
$$|E - (P \times 0.25)| \le 0.05\text{ MWh}$$
Any record violating energy conservation is instantly rejected by PostgreSQL at the engine level.

---

## 5. Duplicate Detection & Disambiguation

### 5.1 Power Plant Alias Standardization

Raw PUCSL spreadsheets contain non-standard station naming across daily sheets (e.g. `"Lakvijaya Coal"`, `"Lakvijaya 1"`, `"LVPS Unit 1"`).
The warehouse resolves these via `ref.plant_alias` using fuzzy normalization into canonical plant codes (e.g. `LAKVIJAYA_1`, `LAKVIJAYA_2`, `LAKVIJAYA_3`), linking reliably to `dw.dim_power_plant`.

### 5.2 Aggregation Double-Counting Guard

CEB Statistical Digests include both disaggregated consumer sectors and aggregated totals (`"Total CEB"`, `"Bulk Supply to LECO"`, `"Total Sales"`).
- In naive ETL, loading summary lines causes a 100% double-count error.
- In `CebDigestParser`, explicit regex filters eliminate aggregate summary rows (`"Total"`, `"System Total"`), while preserving distinct tariff sectors.
- Bulk supply to LECO is categorized under its dedicated conformed sector code `BULK_LECO` to ensure distribution franchisee energy is isolated and not double-counted with retail CEB consumer categories.

---

## 6. Physical Boundary & Outlier Verification

All historical data passed automated physical range gates:
- Active Power: $0 \le P \le P_{\text{installed}}$ (e.g., Victoria Hydro $P \le 210\text{ MW}$, Lakvijaya Coal Unit $P \le 300\text{ MW}$).
- Solar Irradiance: $0 \le G \le 40\text{ MJ/m}^2/\text{day}$.
- Ambient Temperature: $10^\circ\text{C} \le T \le 42^\circ\text{C}$ (consistent with Sri Lankan tropical microclimates).
- Wind Speed: $0 \le v \le 40\text{ m/s}$ at 10m and 50m hub heights.
- Pre-cipitation: $0 \le \text{Rain} \le 500\text{ mm/day}$.
