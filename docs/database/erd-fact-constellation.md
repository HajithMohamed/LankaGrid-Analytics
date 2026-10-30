# Fact Constellation & Schema Entity-Relationship Diagrams

## 1. Complete Kimball Fact Constellation Diagram (`dw` Schema)

Implemented in [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)–[008_facts_weather_and_published.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/008_facts_weather_and_published.sql):

```mermaid
erDiagram
    DIM_DATE ||--o{ FACT_DISPATCH_INTERVAL : "date_key"
    DIM_INTERVAL ||--o{ FACT_DISPATCH_INTERVAL : "interval_key"
    DIM_POWER_PLANT ||--o{ FACT_DISPATCH_INTERVAL : "plant_key"
    DIM_ENERGY_SOURCE ||--o{ FACT_DISPATCH_INTERVAL : "energy_source_key"
    DIM_METRIC ||--o{ FACT_DISPATCH_INTERVAL : "metric_key"
    DIM_SOURCE_SYSTEM ||--o{ FACT_DISPATCH_INTERVAL : "source_system_key"

    DIM_DATE ||--o{ FACT_GENERATION_PERIOD : "period_start_date_key / period_end_date_key"
    DIM_POWER_PLANT ||--o{ FACT_GENERATION_PERIOD : "plant_key"
    DIM_ENERGY_SOURCE ||--o{ FACT_GENERATION_PERIOD : "energy_source_key"
    DIM_METRIC ||--o{ FACT_GENERATION_PERIOD : "metric_key"
    DIM_SOURCE_SYSTEM ||--o{ FACT_GENERATION_PERIOD : "source_system_key"

    DIM_DATE ||--o{ FACT_CAPACITY_PERIOD : "effective_start_date_key / effective_end_date_key"
    DIM_POWER_PLANT ||--o{ FACT_CAPACITY_PERIOD : "plant_key"
    DIM_ENERGY_SOURCE ||--o{ FACT_CAPACITY_PERIOD : "energy_source_key"
    DIM_METRIC ||--o{ FACT_CAPACITY_PERIOD : "metric_key"
    DIM_SOURCE_SYSTEM ||--o{ FACT_CAPACITY_PERIOD : "source_system_key"

    DIM_DATE ||--o{ FACT_ELECTRICITY_SALES : "period_start_date_key / period_end_date_key"
    DIM_REGION ||--o{ FACT_ELECTRICITY_SALES : "region_key"
    DIM_CONSUMPTION_SECTOR ||--o{ FACT_ELECTRICITY_SALES : "sector_key"
    DIM_METRIC ||--o{ FACT_ELECTRICITY_SALES : "metric_key"
    DIM_SOURCE_SYSTEM ||--o{ FACT_ELECTRICITY_SALES : "source_system_key"

    DIM_DATE ||--o{ FACT_WEATHER_DAILY : "date_key"
    DIM_WEATHER_LOCATION ||--o{ FACT_WEATHER_DAILY : "weather_location_key"
    DIM_METRIC ||--o{ FACT_WEATHER_DAILY : "metric_key"
    DIM_SOURCE_SYSTEM ||--o{ FACT_WEATHER_DAILY : "source_system_key"

    DIM_DATE ||--o{ FACT_PUBLISHED_METRIC : "period_start_date_key / period_end_date_key"
    DIM_METRIC ||--o{ FACT_PUBLISHED_METRIC : "metric_key"
    DIM_REGION |o--o{ FACT_PUBLISHED_METRIC : "region_key"
    DIM_ENERGY_SOURCE |o--o{ FACT_PUBLISHED_METRIC : "energy_source_key"
    DIM_CONSUMPTION_SECTOR |o--o{ FACT_PUBLISHED_METRIC : "sector_key"
    DIM_SOURCE_SYSTEM ||--o{ FACT_PUBLISHED_METRIC : "source_system_key"

    DIM_ENERGY_SOURCE ||--o{ DIM_POWER_PLANT : "energy_source_key"
    DIM_REGION |o--o{ DIM_POWER_PLANT : "region_key"
    DIM_REGION ||--o{ DIM_WEATHER_LOCATION : "region_key"
    DIM_REGION |o--o{ DIM_REGION : "parent_region_key"
```

---

## 2. Detailed Sub-Model 1: Generation, Dispatch & Capacity Star Cluster

```mermaid
erDiagram
    DIM_POWER_PLANT {
        int plant_key PK
        varchar plant_code
        varchar plant_name
        varchar entity_level
        varchar operator_type
        int energy_source_key FK
        int region_key FK
        date effective_from
        date effective_to
        boolean is_current
    }
    DIM_ENERGY_SOURCE {
        int energy_source_key PK
        varchar energy_source_code UK
        varchar energy_category
        varchar fuel_type
        boolean is_renewable
        boolean is_dispatchable
    }
    DIM_INTERVAL {
        int interval_key PK
        varchar interval_type
        smallint interval_index
        time start_time
        time end_time
        varchar tariff_time_block
    }
    FACT_DISPATCH_INTERVAL {
        bigint dispatch_fact_id PK
        int date_key PK,FK
        int interval_key FK
        int plant_key FK
        int energy_source_key FK
        int metric_key FK
        int source_system_key FK
        varchar dataset_revision
        timestamptz original_timestamp
        numeric active_power_mw
        numeric derived_energy_mwh
        boolean is_current_revision
        bigint source_document_id FK
        bigint etl_run_id FK
    }
    FACT_GENERATION_PERIOD {
        bigint generation_fact_id PK
        int plant_key FK
        int energy_source_key FK
        int metric_key FK
        varchar period_type_code FK
        int period_start_date_key FK
        int period_end_date_key FK
        numeric generation_mwh
        numeric peak_generation_mw
        varchar generation_boundary
        boolean is_current_revision
    }
    FACT_CAPACITY_PERIOD {
        bigint capacity_fact_id PK
        int plant_key FK
        int energy_source_key FK
        int metric_key FK
        varchar period_type_code FK
        int effective_start_date_key FK
        int effective_end_date_key FK
        numeric installed_capacity_mw
        numeric dependable_capacity_mw
        smallint unit_count
    }

    DIM_ENERGY_SOURCE ||--o{ DIM_POWER_PLANT : classifies
    DIM_POWER_PLANT ||--o{ FACT_DISPATCH_INTERVAL : generates
    DIM_INTERVAL ||--o{ FACT_DISPATCH_INTERVAL : slots
    DIM_POWER_PLANT ||--o{ FACT_GENERATION_PERIOD : produces
    DIM_POWER_PLANT ||--o{ FACT_CAPACITY_PERIOD : rated_at
```

---

## 3. Detailed Sub-Model 2: Sales, Weather & Published Benchmark Cluster

```mermaid
erDiagram
    DIM_REGION {
        int region_key PK
        varchar region_code UK
        varchar region_name
        varchar region_level
        int parent_region_key FK
    }
    DIM_CONSUMPTION_SECTOR {
        int sector_key PK
        varchar sector_code UK
        varchar sector_name
        varchar tariff_group
        boolean is_aggregate_bucket
    }
    DIM_WEATHER_LOCATION {
        int weather_location_key PK
        varchar location_code UK
        varchar energy_zone_type
        int region_key FK
        numeric latitude_deg
        numeric longitude_deg
    }
    FACT_ELECTRICITY_SALES {
        bigint sales_fact_id PK
        int region_key FK
        int sector_key FK
        int metric_key FK
        varchar period_type_code FK
        int period_start_date_key FK
        int period_end_date_key FK
        numeric energy_sold_mwh
        bigint consumer_account_count
        numeric revenue_lkr
    }
    FACT_WEATHER_DAILY {
        bigint weather_fact_id PK
        int date_key FK
        int weather_location_key FK
        int metric_key FK
        varchar source_variable_name
        numeric standardized_value
        varchar missing_value_code
        boolean is_missing
    }
    FACT_PUBLISHED_METRIC {
        bigint published_fact_id PK
        int metric_key FK
        varchar period_type_code FK
        int period_start_date_key FK
        int period_end_date_key FK
        int region_key FK
        int energy_source_key FK
        int sector_key FK
        numeric standardized_value
        boolean is_standalone_published_aggregate
    }

    DIM_REGION ||--o{ FACT_ELECTRICITY_SALES : locates
    DIM_CONSUMPTION_SECTOR ||--o{ FACT_ELECTRICITY_SALES : tariffs
    DIM_REGION ||--o{ DIM_WEATHER_LOCATION : contains
    DIM_WEATHER_LOCATION ||--o{ FACT_WEATHER_DAILY : samples
    DIM_REGION |o--o{ FACT_PUBLISHED_METRIC : scopes
    DIM_CONSUMPTION_SECTOR |o--o{ FACT_PUBLISHED_METRIC : scopes
```

---

## 4. Detailed Sub-Model 3: Provenance (`raw`), `staging`, `ref`, and `audit` Lineage

```mermaid
erDiagram
    RAW_SOURCE_SYSTEM ||--o{ RAW_SOURCE_DOCUMENT : publishes
    RAW_SOURCE_DOCUMENT ||--o{ RAW_INGESTION_BATCH : ingested_in
    RAW_INGESTION_BATCH ||--o{ RAW_EXTRACTED_RECORD : extracts
    RAW_EXTRACTED_RECORD ||--o{ STG_GENERATION_REPORT : populates
    RAW_SOURCE_DOCUMENT ||--o{ AUDIT_ETL_RUN : tracked_by
    REF_DATA_QUALITY_RULE ||--o{ AUDIT_DATA_QUALITY_ISSUE : governs
    AUDIT_ETL_RUN ||--o{ AUDIT_DATA_QUALITY_ISSUE : logs
    AUDIT_ETL_RUN ||--o{ AUDIT_RECONCILIATION_CASE : evaluates
    AUDIT_ETL_RUN ||--o{ AUDIT_RECORD_LINEAGE : traces
    REF_UNIT ||--o{ REF_UNIT_CONVERSION : converts
    REF_REPORTING_PERIOD_TYPE ||--o{ REF_SOURCE_PRECEDENCE : scopes
```

