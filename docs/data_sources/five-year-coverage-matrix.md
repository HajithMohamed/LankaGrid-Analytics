# Five-Year Historical Coverage Matrix (2020–2024)

## 1. Domain Coverage Matrix Across 7 Schemas

This matrix maps temporal granularity, source lineage, warehouse tables, and coverage status across the 5 calendar years (2020 to 2024) for the **GridLens Data Warehouse**.

| Domain / Business Area | Warehouse Fact / Dim Table | Source Provider | Temporal Granularity | 2020 | 2021 | 2022 | 2023 | 2024 | Completeness Status |
|---|---|---|---|---|---|---|---|---|---|
| **Electricity Sales by Tariff** | `dw.fact_electricity_sales` | CEB Statistical Digest | Annual / Sectoral | Yes | Yes | Yes | Yes | Yes | 100% (5/5 years, 44 sector-year series) |
| **Consumer Accounts** | `dw.fact_electricity_sales` (consumers) | CEB Statistical Digest | Annual / Sectoral | Yes | Yes | Yes | Yes | Yes | 100% (5/5 years, 44 sector-year series) |
| **Solar & Meteorological** | `dw.fact_weather_daily` | NASA POWER API | Daily Point Observations | Yes | Yes | Yes | Yes | Yes | 100% (1,827 days, 21,924 observations) |
| **National Installed Capacity** | `dw.fact_capacity_period` / `dw.fact_published_metric` | CEB Statistical Digest | Annual / Technology | Yes | Yes | Yes | Yes | Yes | 100% (5/5 years) |
| **National Peak Demand** | `dw.fact_published_metric` | CEB Statistical Digest & PUCSL | Annual & Daily Peak | Yes | Yes | Yes | Yes | Yes | 100% (5/5 years) |
| **Sub-Daily Unit Dispatch** | `dw.fact_dispatch_interval` | PUCSL 15-Minute Reports | 15-Minute Interval | Part* | Part* | Part* | Part* | Yes (Mar) | Target Month Complete (31 days, 10,365 interval rows) |
| **Daily Plant Generation** | `dw.fact_generation_period` | PUCSL Daily Reports | Daily Plant Total | Part* | Part* | Part* | Part* | Yes (Dec) | Operational baseline established |

*\* Note on Historical Dispatch Archives: PUCSL public web portal provides sub-daily spreadsheets intermittently. The warehouse schema features forward range partitioning for years 2020 through 2025 (`dw.fact_dispatch_interval_y2020` to `_y2025`) enabling rapid, idempotent ingestion as additional monthly archives are retrieved.*

---

## 2. Sectoral Electricity Consumption Breakdown (2020–2024)

Audited electricity sales in GWh ($1\text{ GWh} = 1{,}000\text{ MWh}$) from CEB Annual Statistical Digests:

| Tariff / Consumer Category | Sector Code | 2020 (GWh) | 2021 (GWh) | 2022 (GWh) | 2023 (GWh) | 2024 (GWh) | 5-Year CAGR / Trend |
|---|---|---|---|---|---|---|---|
| **Domestic** | `DOMESTIC` | 5,443.0 | 5,593.0 | 5,234.0 | 4,895.8 | 5,124.7 | Macro contraction 2022-2023; rebound in 2024 |
| **Industrial** | `INDUSTRIAL` | 4,557.0 | 4,960.0 | 4,591.0 | 4,374.0 | 4,789.2 | Resilient industrial consumption post-2023 |
| **General Purpose** | `COMMERCIAL` | 2,752.0 | 3,025.0 | 2,987.0 | 2,985.4 | 3,186.4 | Consistent commercial demand driver |
| **Hotel / Tourism** | `HOTEL` | 276.0 | 258.0 | 308.0 | 385.2 | 476.3 | Rapid post-pandemic tourism recovery (+84.6%) |
| **Religious** | `RELIGIOUS` | 89.0 | 92.0 | 95.0 | 88.5 | 94.2 | Stable non-commercial social consumption |
| **Street Lighting** | `STREET_LIGHTING` | 48.0 | 52.0 | 47.0 | 39.4 | 42.8 | Energy efficiency & LED conversion initiatives |
| **Government / Public** | `GOVERNMENT` | 1,122.0 | 1,234.0 | 1,258.0 | 1,385.2 | 1,476.9 | Steady civic utility growth |
| **Bulk Supply to LECO** | `BULK_LECO` | *(Aggregated)* | *(Aggregated)* | *(Audited)* | 1,514.0 | 1,601.2 | Segregated distribution franchisee sales |
| **Total National Sales** | `ALL_SECTORS` | **14,287.0** | **15,214.0** | **14,520.0** | **14,153.5** | **15,190.5** | **Total reconciles to published digest totals** |

---

## 3. NASA POWER Meteorological & Solar 5-Year Coverage

### 3.1 Temporal Continuity
- **Period**: 2020-01-01 to 2024-12-31
- **Total Calendar Days**: 1,827 days (including leap years 2020 and 2024)
- **Missing Days**: 0 days (100% daily continuity)
- **Total Observations**: 21,924 parameter observations ($1,827\text{ days} \times 6\text{ parameters} \times 2\text{ nodes}$)

### 3.2 Observed Annual Solar Irradiance Summary ($MJ/m^2/day$)

| Year | Victoria Hydro (Central Hills) Min / Mean / Max | Mannar Wind Corridor (North Coast) Min / Mean / Max | National Trend |
|---|---|---|---|
| **2020** | 4.86 / 17.82 / 27.43 | 6.12 / 20.45 / 29.88 | Peak insolation Feb–April; monsoon suppression Jun–Aug |
| **2021** | 3.92 / 17.45 / 26.98 | 5.84 / 20.12 / 29.41 | Active Southwest Monsoon in central highlands |
| **2022** | 4.15 / 17.68 / 27.15 | 6.01 / 20.38 / 29.72 | Typical bimodal tropical monsoon pattern |
| **2023** | 4.62 / 18.01 / 27.89 | 6.35 / 20.84 / 30.15 | Enhanced dry season irradiance |
| **2024** | 4.41 / 17.94 / 27.65 | 6.20 / 20.65 / 30.02 | Consistent insolation supporting utility & rooftop solar |

---

## 4. Operational Dispatch Granularity (PUCSL March 2024)

- **Total Days**: 31 full calendar days (2024-03-01 through 2024-03-31)
- **Intervals per Day**: 96 intervals (every 15 minutes: 00:00 to 23:45 SLST)
- **Total Interval Records Loaded**: 10,365 records
- **Power Stations Tracked**: 50 unique generating stations across Major Hydro, Thermal Coal, Thermal Oil, IPP, Wind, and Solar.
- **Physical Bounds Enforced**: Active power $P \ge 0\text{ MW}$, energy $E = P \times 0.25\text{ MWh} \pm 0.05$.
- **Zero vs Missing Distinction**: Exact $0\text{ MW}$ values are preserved as genuine plant offline/curtailment states; unmeasured intervals are tracked as `NULL` with `value_status = 'MISSING'`.
