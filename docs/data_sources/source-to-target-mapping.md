# Source-to-Target Mapping Specification

This document defines the exact end-to-end lineage from official upstream publications ([source-inventory.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/source-inventory.md)) through `raw`, `staging`, and `ref` into the Kimball `dw` Fact Constellation ([005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)–[009_staging_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql)).

---

## 1. Provenance Metadata Mapping (`data/raw/manifest.json` -> `raw.*`)

| Manifest / File Attribute | Staging / Registry Target | Transformation & Validation Rule |
|---|---|---|
| `provider` | `raw.source_system.source_code`, `dw.dim_source_system.source_code` | Canonical uppercase provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| `source_id` | `raw.source_document.document_code` | Unique natural document identifier. |
| `source_url` | `raw.source_document.source_url` | Exact HTTP/HTTPS provenance URL. |
| `original_filename` | `raw.source_document.original_filename` | Preserved verbatim; raw file stored read-only under `data/raw/`. |
| `sha256_checksum` | `raw.source_document.sha256_checksum` | Verified 64-hex SHA-256 upon download (`DOWNLOADED_VERIFIED`). |
| `reporting_period` | `raw.source_document.reporting_period_start`, `reporting_period_end` | Parsed into explicit ISO start/end `DATE` bounds. |
| Extracted row/cell JSON | `raw.extracted_record.raw_payload`, `source_row_locator` | Stored verbatim as `JSONB` with `page/table/row` or `json_path` locator. |

---

## 2. Operational Sub-Daily Dispatch (`PUCSL` -> `dw.fact_dispatch_interval`)

| Upstream Source & Field | Staging Column (`staging.stg_dispatch_observation`) | Reference Lookup (`ref.*` / `etl.*`) | Warehouse Target (`dw.fact_dispatch_interval`) |
|---|---|---|---|
| PUCSL Daily Report 15-min timestamp (`00:00`..`23:45` SLST) | `raw_timestamp_text` -> `parsed_timestamp` | `etl.fn_normalize_interval_15min()` | `date_key` (`dw.dim_date`), `interval_key` (`dw.dim_interval`), `original_timestamp` |
| Generation plant / dispatch group label | `raw_entity_name` | `ref.plant_alias` (`VERIFIED`) -> `dw.dim_power_plant` | `plant_key`, `energy_source_key` |
| Active dispatch / System demand (`MW`) | `raw_power_text` -> `parsed_power_mw` | Missing sentinels (`-`, `N/A`) -> `NULL` (`value_status='MISSING'`); never `0` | `active_power_mw`, `reported_value`, `reported_unit_code='MW'` |
| Integrated 15-min energy (optional) | Derived only if explicitly enabled | `etl.fn_convert_unit(mw, 'MW', 'MWh', 0.25)` | `derived_energy_mwh`, `is_energy_derived=TRUE` |

---

## 3. Periodic Plant & Category Generation (`PUCSL` & `CEB` -> `dw.fact_generation_period`)

| Upstream Source & Field | Staging Column (`staging.stg_generation_report`) | Reference Lookup (`ref.*` / `etl.*`) | Warehouse Target (`dw.fact_generation_period`) |
|---|---|---|---|
| PUCSL Station Daily Generation (`MWh`) | `raw_generation_text`, `reported_unit_code='MWh'`, `period_type_code='DAILY'` | `etl.fn_validate_reporting_period('DAILY', d, d)` | `generation_mwh`, `period_type_code='DAILY'`, `period_start_date_key = period_end_date_key` |
| PUCSL Station Daily Peak (`MW`) | `raw_peak_mw_text` -> `parsed_peak_mw` | Physical bound check $0 \le P_{\text{peak}} \le 1.05 \times P_{\text{installed}}$ | `peak_generation_mw` |
| CEB Digest Monthly / Annual Generation (`GWh`) | `raw_generation_text`, `reported_unit_code='GWh'`, `period_type_code IN ('MONTHLY','ANNUAL')` | `etl.fn_convert_unit(val, 'GWh', 'MWh', NULL)` ($\times 1{,}000$) | `generation_mwh` (in `MWh`), `reported_source_value` (in `GWh`), `reported_unit_code='GWh'` |
| Gross vs. Net table header | `generation_boundary` | `dw.dim_metric` (`GROSS_GENERATION_MWH` vs `NET_GENERATION_MWH`) | `metric_key`, `generation_boundary` |

---

## 4. Installed & Dependable Capacity (`CEB` & `PUCSL` -> `dw.fact_capacity_period`)

| Upstream Source & Field | Staging Column (`staging.stg_plant_capacity`) | Reference Lookup | Warehouse Target (`dw.fact_capacity_period`) |
|---|---|---|---|
| Plant / Technology Name | `raw_plant_name` | `ref.plant_alias` -> `dw.dim_power_plant` | `plant_key`, `energy_source_key` |
| Installed Capacity (`MW`) | `parsed_installed_mw` | `dw.dim_metric` (`INSTALLED_CAPACITY_MW`) | `installed_capacity_mw` |
| Effective / Dependable Capacity (`MW`) | `parsed_dependable_mw` | Checked `<= installed_capacity_mw` | `dependable_capacity_mw` |
| Number of Generating Units | `parsed_unit_count` | Non-negative integer check | `unit_count` |

---

## 5. Electricity Sales & Consumer Accounts (`CEB` -> `dw.fact_electricity_sales`)

| Upstream Source & Field | Staging Column (`staging.stg_electricity_sales`) | Reference Lookup | Warehouse Target (`dw.fact_electricity_sales`) |
|---|---|---|---|
| Province / Distribution Division (`DD1`–`DD4` or National) | `raw_region_name` | `ref.region_alias` -> `dw.dim_region` (defaults to `LK` if national-only) | `region_key` |
| Consumer Tariff Category (`Domestic`, `Industrial`, `GP`, `Hotel`, etc.) | `raw_sector_name` | `dw.dim_consumption_sector` (`ALL_SECTORS` if provincial-only total) | `sector_key` |
| Billed Units Sold (`GWh`) | `parsed_energy_sold`, `reported_unit_code='GWh'` | `etl.fn_convert_unit(val, 'GWh', 'MWh', NULL)` | `energy_sold_mwh`, `reported_energy_value`, `reported_energy_unit_code` |
| Consumer Accounts Count | `parsed_consumer_count` | Semi-additive validation (`>= 0`) | `consumer_account_count` |
| Tariff Revenue (`LKR Mn`, when published) | `parsed_revenue_lkr` | `etl.fn_convert_unit(val, 'MLKR', 'LKR', NULL)` | `revenue_lkr` (`NULL` if unpublished) |

---

## 6. Meteorological Daily Observations (`NASA POWER` -> `dw.fact_weather_daily`)

| NASA POWER JSON Field | Staging Column (`staging.stg_weather_observation`) | Reference Lookup | Warehouse Target (`dw.fact_weather_daily`) |
|---|---|---|---|
| Sampling coordinate / node code | `location_code` | `dw.dim_weather_location` ($5.8^\circ\text{–}10.0^\circ\text{N}$, $79.4^\circ\text{–}82.0^\circ\text{E}$) | `weather_location_key` |
| `YYYYMMDD` key in `properties.parameter.<VAR>` | `observation_date` | `dw.dim_date` | `date_key` |
| Parameter code (`ALLSKY_SFC_SW_DWN`, `T2M`, `PRECTOTCORR`, `WS10M`, `RH2M`) | `source_variable_name` | `ref.metric_mapping` -> `dw.dim_metric` | `metric_key`, `source_variable_name` |
| Parameter numeric value or `-999.0` | `parsed_value`, `missing_value_code` | If `-999` / `-999.0`: set `is_missing=TRUE`, `standardized_value=NULL`, `missing_value_code='-999.0'` | `standardized_value`, `original_reported_value`, `missing_value_code`, `is_missing` |

---

## 7. Published Aggregate Benchmarks (`CEB` & `PUCSL` -> `dw.fact_published_metric`)

| Upstream Source & Field | Staging Column (`staging.stg_published_statistic`) | Reference Lookup | Warehouse Target (`dw.fact_published_metric`) |
|---|---|---|---|
| Headline Digest Summary (e.g., System Loss `%`, Annual Peak `MW`, Total Gross `GWh`) | `metric_code`, `parsed_published_value`, `published_unit_code`, `publication_table_ref` | `dw.dim_metric` + `etl.fn_convert_unit` where applicable | `standardized_value`, `published_value`, `is_standalone_published_aggregate=TRUE` |
