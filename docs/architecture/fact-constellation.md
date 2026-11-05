# Kimball Fact Constellation Architecture

## Dimensional Bus Matrix

The GridLens data warehouse adheres strictly to Ralph Kimball's dimensional bus architecture. Nine conformed dimensions intersect across six distinct business process facts.

| Business Process Fact Table | `dim_date` | `dim_time_of_day` | `dim_power_plant` | `dim_generation_unit` | `dim_fuel_type` | `dim_grid_substation` | `dim_transmission_line` | `dim_tariff_customer_class` | `dim_administrative_area` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`fact_dispatch_interval`** | **X** | **X** | **X** | **X** | **X** | **X** | | | |
| **`fact_generation_period`** | **X** | | **X** | | **X** | | | | |
| **`fact_capacity_period`** | **X** | | **X** | **X** | **X** | | | | |
| **`fact_electricity_sales`** | **X** | | | | | | | **X** | **X** |
| **`fact_weather_daily`** | **X** | | | | | **X** | | | |
| **`fact_published_metric`** | **X** | | | | | | | | |

---

## Fact Constellation Architecture Diagram

```mermaid
graph TD
    classDef dim fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef fact fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef mart fill:#312e81,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc;

    %% Conformed Dimensions
    D_DATE["dim_date<br/>(date_id)"]:::dim
    D_TIME["dim_time_of_day<br/>(time_id)"]:::dim
    D_PLANT["dim_power_plant<br/>(plant_id, SCD Type 2)"]:::dim
    D_UNIT["dim_generation_unit<br/>(unit_id)"]:::dim
    D_FUEL["dim_fuel_type<br/>(fuel_type_id)"]:::dim
    D_SUB["dim_grid_substation<br/>(grid_substation_id)"]:::dim
    D_TARIFF["dim_tariff_customer_class<br/>(customer_class_id)"]:::dim
    D_AREA["dim_administrative_area<br/>(area_id)"]:::dim

    %% Fact Tables
    F_DISPATCH["dw.fact_dispatch_interval<br/>(15-Minute SCADA Telemetry)"]:::fact
    F_GEN["dw.fact_generation_period<br/>(Periodic Plant Generation)"]:::fact
    F_CAP["dw.fact_capacity_period<br/>(Dependable & Peak Capacity)"]:::fact
    F_SALES["dw.fact_electricity_sales<br/>(Provincial Billed Sales)"]:::fact
    F_WEATHER["dw.fact_weather_daily<br/>(NASA Solar & Weather)"]:::fact
    F_METRIC["dw.fact_published_metric<br/>(System Macro KPIs)"]:::fact

    %% Analytical Marts
    M_DAILY["mart.mv_daily_system_summary"]:::mart
    M_FUEL["mart.mv_monthly_fuel_mix"]:::mart
    M_DISPATCH["mart.mv_hourly_dispatch_pattern"]:::mart
    M_CORR["mart.mv_weather_correlation_summary"]:::mart

    %% Relationships: Dispatch
    D_DATE --> F_DISPATCH
    D_TIME --> F_DISPATCH
    D_PLANT --> F_DISPATCH
    D_UNIT --> F_DISPATCH
    D_FUEL --> F_DISPATCH
    D_SUB --> F_DISPATCH

    %% Relationships: Generation & Capacity
    D_DATE --> F_GEN
    D_PLANT --> F_GEN
    D_FUEL --> F_GEN

    D_DATE --> F_CAP
    D_PLANT --> F_CAP
    D_UNIT --> F_CAP
    D_FUEL --> F_CAP

    %% Relationships: Sales
    D_DATE --> F_SALES
    D_TARIFF --> F_SALES
    D_AREA --> F_SALES

    %% Relationships: Weather
    D_DATE --> F_WEATHER
    D_SUB --> F_WEATHER

    %% Relationships: Published Metrics
    D_DATE --> F_METRIC

    %% Mart rollups
    F_DISPATCH --> M_DAILY
    F_DISPATCH --> M_DISPATCH
    F_DISPATCH --> M_FUEL
    F_WEATHER --> M_CORR
```

---

## Architectural Principles

1. **Grain Isolation**: Every fact table records measurements at an immutable, uniform grain. Sub-daily 15-minute dispatch ($MW$) is never stored in the same table as monthly sales ($GWh$).
2. **Conformed Dimensions**: Shared attributes such as `dim_date`, `dim_fuel_type`, and `dim_grid_substation` maintain single source-of-truth definitions across all facts, enabling cross-domain joins without bridge tables.
3. **Surrogate Keys**: Integer surrogate primary keys isolate the analytical schema from changing natural keys in upstream utility systems.
4. **Physical Partitioning**: High-volume facts (`fact_dispatch_interval`) use declarative range partitioning by year to maximize query performance and partition pruning in PostgreSQL.
5. **Separation of Schemas**:
   - `raw`: Cryptographic provenance and unmutated payload ingestion.
   - `staging`: Typed transformation and boundary validation.
   - `ref`: Reference taxonomies and quality rules.
   - `dw`: Conformed facts and dimensions.
   - `mart`: Pre-aggregated materialized views and grain-safe query views.
   - `audit`: Data quality exception ledger and ETL pipeline history.

