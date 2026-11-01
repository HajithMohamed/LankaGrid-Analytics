# Phase 3 Analytical Query Catalogue (Q01–Q24)
## GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka

This catalogue documents all 24 analytical queries designed and implemented across six engineering team members for **Phase 3 (Business Intelligence, Advanced OLAP, and Historical Data Analysis)**. Each query answers authentic grid operational, economic, or data quality business questions using verified historical data (2020–2024 CEB Sales, 2020–2024 NASA POWER Weather, and March 2024 PUCSL 15-Minute Dispatch).

---

## Member 1: Grid Generation Mix & Renewable Penetration

### [Q01: Generation Mix by Energy Source (March 2024)](../../database/queries/phase3/member_01_generation/Q01.sql)
- **Business Question**: What was the total energy generation (MWh and %) by energy source and fuel type for March 2024?
- **Relevance**: Evaluates national dependency on fossil fuels vs. clean renewables and validates fuel diversification strategies.
- **Academic Lecture Mapping**: Lecture 8 (Hierarchical ROLLUP from fuel type to major category), Lecture 3 (Fact Grain).
- **Fact Grain**: Monthly aggregated technology and fuel type totals from 15-minute intervals.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $\text{Energy MWh} = \sum(\text{active\_power\_mw} \times 0.25)$, $\text{Share \%} = \frac{\text{Category MWh}}{\text{Total MWh}} \times 100\%$.

### [Q02: Daily Renewable vs Non-Renewable Penetration (March 2024)](../../database/queries/phase3/member_01_generation/Q02.sql)
- **Business Question**: How did the renewable energy penetration percentage vary daily across March 2024?
- **Relevance**: Analyzes daily grid variability and tracks progress toward Sri Lanka's policy target of 70% renewable generation by 2030.
- **Academic Lecture Mapping**: Lecture 1 (Time-Variant Historical Analysis), Lecture 5 (7-Day Centered Moving Average Window).
- **Fact Grain**: Daily energy aggregation by renewable classification.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $\text{Renewable \%} = \frac{\sum \text{MWh}_{\text{renewable}}}{\sum \text{MWh}_{\text{total}}} \times 100\%$, $\text{MA}_{7d} = \text{AVG}(\text{Share}) \text{ OVER (ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING)}$.

### [Q03: Plant Capacity Factor Analysis (March 2024)](../../database/queries/phase3/member_01_generation/Q03.sql)
- **Business Question**: What is the realized capacity factor for major generation plants relative to verified reference installed capacity?
- **Relevance**: Identifies plant utilization efficiency, underperforming thermal or hydro assets, and baseload availability.
- **Academic Lecture Mapping**: Lecture 3 & 4 (Fact Constellation: joining plant reference ratings with operational dispatch facts), Lecture 6 (Boundary Ratings).
- **Fact Grain**: Monthly aggregate plant energy vs. maximum theoretical potential ($P_{\text{installed}} \times 744\text{ hours}$).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $\text{Capacity Factor \%} = \frac{\text{Actual Generation (MWh)}}{\text{Installed Capacity (MW)} \times 744\text{ hours}} \times 100\%$.

### [Q04: Peak vs Off-Peak Generation Contribution (March 2024)](../../database/queries/phase3/member_01_generation/Q04.sql)
- **Business Question**: How does each generation source contribute to Day, Peak, and Off-Peak Time-of-Use (TOU) windows?
- **Relevance**: Measures peaking capability and identifies which thermal or hydro assets meet the expensive 18:30–22:30 evening demand surge.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Slicing by Time-of-Use regime), Lecture 3 (TOU Dimensional Slicing).
- **Fact Grain**: 15-minute interval dispatch classified by TOU tariff bucket.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_interval`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: Conditional TOU energy sum and percentage: $\text{TOU Share \%} = \frac{\text{MWh}_{\text{regime}}}{\sum \text{MWh}_{\text{regime}}} \times 100\%$.

---

## Member 2: Grid Dispatch Dynamics & 15-Minute Load Profiles

### [Q05: 15-Minute Diurnal Dispatch Curves — Weekday vs Weekend](../../database/queries/phase3/member_02_dispatch/Q05.sql)
- **Business Question**: What is the average 24-hour diurnal dispatch curve for weekdays compared to weekends across March 2024?
- **Relevance**: Determines base, intermediate, and peak loading cycles, revealing industrial shutdown effects on weekend load profiles.
- **Academic Lecture Mapping**: Lecture 2 (Slice and Dice across calendar type dimension `is_weekend`), Lecture 5 (Diurnal Load Profiling).
- **Fact Grain**: 15-minute interval slot (1 to 96) averaged across calendar day types (21 weekdays, 10 weekend days).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_interval`, `dw.dim_date`.
- **Formulas**: $\overline{P}_{\text{slot}} = \text{AVG}(\sum_{\text{plants}} \text{active\_power\_mw})$.

### [Q06: 15-Minute Dispatch Ramp Rate Analysis](../../database/queries/phase3/member_02_dispatch/Q06.sql)
- **Business Question**: What are the steepest 15-minute positive and negative grid ramp rates (MW/interval and MW/min)?
- **Relevance**: Informs grid operators of ramping stress, fast-start hydro spinning reserve requirements, and solar sunset drop-offs.
- **Academic Lecture Mapping**: Lecture 5 (Analytical Window Functions `LAG()` ordered by temporal sequence).
- **Fact Grain**: Chronological 15-minute system dispatch timestamp delta.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_interval`, `dw.dim_date`.
- **Formulas**: $\Delta P = P_t - P_{t-1}$, $\text{Ramp Rate (MW/min)} = \frac{\Delta P}{15\text{ min}}$.

### [Q07: Baseload vs Peaking Plant Operational Behavior](../../database/queries/phase3/member_02_dispatch/Q07.sql)
- **Business Question**: Which power plants operate continuously as baseload assets versus cycling/peaking assets?
- **Relevance**: Characterizes plant duty cycles (baseload vs. load-following vs. peaking) using operational availability and coefficient of variation ($CV$).
- **Academic Lecture Mapping**: Lecture 5 (Descriptive Statistics: Standard Deviation, Mean, and Relative Dispersion $CV$).
- **Fact Grain**: Plant-level 15-minute dispatch across 2,976 intervals in March 2024.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $CV = \frac{\sigma}{\mu}$, $\text{Availability Factor} = \frac{\text{Intervals online}}{\text{Total intervals}} \times 100\%$.

### [Q08: Telemetry to Published Energy Reconciliation & Scope Variance](../../database/queries/phase3/member_02_dispatch/Q08.sql)
- **Business Question**: What explains the difference between integrated 15-minute SCADA telemetry readings and published daily utility generation totals?
- **Relevance**: Reconciles high-frequency SCADA telemetry with audited daily utility settlement sheets, isolating untelemetered rooftop solar and mini-hydro.
- **Academic Lecture Mapping**: Lecture 6 (Source Conflict Resolution and Multi-Source Reconciliation), Lecture 5 (Residual Analysis).
- **Fact Grain**: Daily energy reconciliation by energy category and system aggregate.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $\text{Variance (MWh)} = \text{Published MWh} - \text{Telemetered MWh}$, $\text{Variance \%} = \frac{\text{Variance}}{\text{Published}} \times 100\%$.

---

## Member 3: Sectoral Electricity Sales & Demand Dynamics

### [Q09: Five-Year Sectoral Electricity Sales Trends (2020–2024)](../../database/queries/phase3/member_03_sales/Q09.sql)
- **Business Question**: How did electricity sales change across consumer categories from 2020 to 2024?
- **Relevance**: Evaluates national electricity demand trajectories through the COVID-19 pandemic, 2022 economic crisis, and tariff hikes.
- **Academic Lecture Mapping**: Lecture 1 (Historical Non-Volatile Warehouse Storage), Lecture 5 (Window `LAG()` for YoY Growth).
- **Fact Grain**: Annual billed sales volume per consumption sector (excluding `ALL_SECTORS`).
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\text{YoY Growth \%} = \frac{S_t - S_{t-1}}{S_{t-1}} \times 100\%$.

### [Q10: Compound Annual Growth Rate (CAGR) by Sector (2020–2024)](../../database/queries/phase3/member_03_sales/Q10.sql)
- **Business Question**: What was the Compound Annual Growth Rate (CAGR) and net volume change for each consumer category?
- **Relevance**: Provides annualized medium-term growth benchmarks for capacity expansion planning and long-term transmission modeling.
- **Academic Lecture Mapping**: Lecture 5 (Mathematical Modeling and Exponential Window Aggregation).
- **Fact Grain**: Sectoral sales endpoints across 5 calendar years (2020 to 2024).
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\text{CAGR} = \left(\frac{S_{2024}}{S_{2020}}\right)^{\frac{1}{4}} - 1$, $\Delta S = S_{2024} - S_{2020}$.

### [Q11: Sectoral Consumption Shifts and Demand Elasticity (2020–2024)](../../database/queries/phase3/member_03_sales/Q11.sql)
- **Business Question**: How has the structural composition of electricity sales shifted between pre-crisis (2020) and recovery (2024)?
- **Relevance**: Measures macroeconomic structural transformations, such as the growth in tourism/hospitality vs. contraction in domestic demand.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Comparative Slice), Lecture 8 (Structural Percentage Decomposition).
- **Fact Grain**: Category market share percentage across milestone years.
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\Delta \text{Share (pp)} = \text{Share}_{2024} - \text{Share}_{2020}$.

### [Q12: CEB Retail vs LECO Bulk Supply Reconciliation (2020–2024)](../../database/queries/phase3/member_03_sales/Q12.sql)
- **Business Question**: What proportion of national electricity sales was distributed directly by CEB versus LECO bulk supply?
- **Relevance**: Details the distribution split between CEB direct customer retail areas and LECO coastal franchise areas.
- **Academic Lecture Mapping**: Lecture 6 (Non-Double Counting: separating LECO bulk resale from CEB direct retail).
- **Fact Grain**: Annual sales split between CEB retail and LECO bulk supply.
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\text{LECO Share \%} = \frac{\text{LECO GWh}}{\text{National Total GWh}} \times 100\%$.

---

## Member 4: Weather Impacts & Renewable Resource Correlation

### [Q13: Five-Year Solar Irradiance Profiles Across Climate Zones](../../database/queries/phase3/member_04_weather/Q13.sql)
- **Business Question**: How does daily and monthly solar irradiance (GHI) vary across Sri Lanka's climatic zones?
- **Relevance**: Identifies optimal geographical locations for utility-scale solar PV development and quantifies seasonal monsoon cloud attenuation.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Roll-Up from daily weather observations to annual geographic aggregations).
- **Fact Grain**: Annual meteorological observations across monitoring nodes (2020–2024, 1,827 days).
- **Tables Consulted**: `dw.fact_weather_daily`, `dw.dim_weather_location`, `dw.dim_date`, `dw.dim_metric`.
- **Formulas**: $\text{Peak Sun Hours (PSH)} = \frac{\text{GHI (MJ/m}^2\text{/day)}}{3.6}$.

### [Q14: Correlation Between Temperature and Peak Electricity Demand](../../database/queries/phase3/member_04_weather/Q14.sql)
- **Business Question**: Is there a measurable relationship between ambient temperature and daily grid demand, and how has thermal variability evolved?
- **Relevance**: Evaluates temperature sensitivity on Sri Lanka's transmission network during pre-monsoon dry season conditions.
- **Academic Lecture Mapping**: Lecture 5 (Statistical Correlation Analysis using `CORR()`), Lecture 3 (Fact Constellation Joins).
- **Fact Grain**: Daily maximum grid demand ($MW$) and integrated daily energy ($MWh$) paired with daily temperature ($^\circ C$).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.fact_weather_daily`, `dw.dim_weather_location`, `dw.dim_metric`, `dw.dim_date`.
- **Formulas**: Pearson correlation coefficient $r = \text{CORR}(T, P)$.

### [Q15: Rainfall and Solar Monsoon Seasonality (CUBE Aggregation)](../../database/queries/phase3/member_04_weather/Q15.sql)
- **Business Question**: How do precipitation and solar irradiance vary simultaneously across geographical locations and Sri Lanka's monsoon seasons?
- **Relevance**: Evaluates hydro storage replenishment and solar output trade-offs across Southwest, Northeast, and Inter-Monsoon periods.
- **Academic Lecture Mapping**: Lecture 8 (Multidimensional CUBE Operator: Location $\times$ Season).
- **Fact Grain**: 2D Data Cube cells across Location and Monsoon Season.
- **Tables Consulted**: `dw.fact_weather_daily`, `dw.dim_weather_location`, `dw.dim_metric`, `dw.dim_date`.
- **Formulas**: 15-cell cube generated via `GROUP BY CUBE (dwl.location_name, dd.sl_monsoon_season)`.

### [Q16: Wind Resource Distribution and March Generation Relationship](../../database/queries/phase3/member_04_weather/Q16.sql)
- **Business Question**: How does measured 50m wind speed compare with actual available wind-generation observations during matching dates?
- **Relevance**: Validates satellite meteorological datasets against real utility-scale wind plant generation in the Mannar wind corridor.
- **Academic Lecture Mapping**: Lecture 4 (Fact-to-Fact Date-Aligned Join), Lecture 5 (Bivariate Correlation & Kinetic Proxy $v^3$).
- **Fact Grain**: Daily energy output ($MWh$) joined with daily mean 50m wind speed ($m/s$) for March 2024.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.fact_weather_daily`, `dw.dim_energy_source`, `dw.dim_weather_location`, `dw.dim_metric`, `dw.dim_date`.
- **Formulas**: $r(v, E) = \text{CORR}(v, E)$, $r(v^3, E) = \text{CORR}(v^3, E)$.

---

## Member 5: Power Plant Performance & Operational Efficiency

### [Q17: Daily Operating Duty Cycle & Online Availability](../../database/queries/phase3/member_05_plant_operations/Q17.sql)
- **Business Question**: What was the daily operating duty cycle, online availability, and zero-generation interval distribution across all grid plants?
- **Relevance**: Evaluates base, cycling, and peaking plant availability, distinguishing true zero generation from missing telemetry.
- **Academic Lecture Mapping**: Lecture 6 (True Zero vs. Missing Data Sentinel Handling), Lecture 5 (Availability Metrics).
- **Fact Grain**: Plant-level operational intervals over 2,976 slots in March 2024.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $\text{Online Duty Cycle \%} = \frac{\text{Intervals with } P > 0}{2{,}976} \times 100\%$.

### [Q18: Power Plant Peak Dispatch vs Installed Nameplate Capacity Analysis](../../database/queries/phase3/member_05_plant_operations/Q18.sql)
- **Business Question**: How does observed peak dispatch compare with historically valid installed capacity?
- **Relevance**: Determines whether thermal and hydro stations achieve their rated nameplate output or suffer derating / transmission bottlenecks.
- **Academic Lecture Mapping**: Lecture 3 (Physical Dimension Attributes & Non-Additive Ratios), Lecture 5 (Capacity Envelope Ranking).
- **Fact Grain**: Plant-level peak and mean operational output over 744 operating hours.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_date`.
- **Formulas**: $\text{Peak-to-Nameplate Ratio \%} = \frac{P_{\text{observed, max}}}{P_{\text{installed}}} \times 100\%$.

### [Q19: Hydro Storage Inflow-to-Generation Response Dynamics](../../database/queries/phase3/member_05_plant_operations/Q19.sql)
- **Business Question**: How did the Mahaweli and Laxapana hydro cascades modulate their dispatch during dry pre-monsoon storage conditions?
- **Relevance**: Evaluates cascade management, reservoir depletion risk, and dispatch continuity.
- **Academic Lecture Mapping**: Lecture 2 (Cascade Hierarchy Roll-Up), Lecture 5 (Time-Series Hydro Dynamics).
- **Fact Grain**: Cascade complex daily energy totals.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $\text{Cascade Energy (MWh)} = \sum_{\text{plant} \in \text{cascade}} \text{MWh}$.

### [Q20: Thermal Generation Merit Order Base vs Peaking Plant Utilization](../../database/queries/phase3/member_05_plant_operations/Q20.sql)
- **Business Question**: Which generation facilities serve predominantly as peaking plants rather than round-the-clock baseload during evening peak hours?
- **Relevance**: Proves economic merit-order behavior: low-cost coal dispatched continuously, while high-cost oil/GTs operate strictly as peaking reserves.
- **Academic Lecture Mapping**: Lecture 3 (Merit-Order Baseload vs Peaking Roles), Lecture 5 (Peaking Duty Ratio).
- **Fact Grain**: Station-level average power during Evening Peak (18:30–22:30) vs. Daytime (05:30–18:30).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_interval`, `dw.dim_date`.
- **Formulas**: $\text{Peaking Duty Index} = \frac{\overline{P}_{\text{Peak}}}{\overline{P}_{\text{Daytime}}}$.

---

## Member 6: Grid Efficiency, Reconciliation & Data Quality

### [Q21: Five-Year Grid Sales Efficiency & Productive Demand Share Analysis (2020–2024)](../../database/queries/phase3/member_06_grid_efficiency/Q21.sql)
- **Business Question**: How did the sectoral distribution of billed electricity consumption, productive economic demand share, and system sales intensity evolve between 2020 and 2024?
- **Relevance**: Productive demand share (Industrial + Commercial + Hotel vs Domestic) is the key utility efficiency metric indicating economic value generated per unit of electricity sold.
- **Academic Lecture Mapping**: Lecture 8 (Data Cube Generation with GROUPING SETS), Lecture 3 (Avoiding Aggregate Double-Counting).
- **Fact Grain**: Multi-level aggregation across Sector Tariff Group and Calendar Year.
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\text{Annual Share \%} = \frac{\text{Sales}_{\text{class, year}}}{\text{Sales}_{\text{year, total}}} \times 100\%$.

### [Q22: Estimated Transmission & Distribution Loss Proxy Analysis (2020–2024)](../../database/queries/phase3/member_06_grid_efficiency/Q22.sql)
- **Business Question**: What was the annual gap between total gross generated electricity and billed final consumption from 2020 to 2024?
- **Relevance**: Evaluates national transmission and distribution (T&D) loss trends and system efficiency improvements.
- **Academic Lecture Mapping**: Lecture 1 & 4 (Cross-Process Constellation Reconciliation between Generation and Sales).
- **Fact Grain**: Annual gross generation ($GWh$) vs. billed retail sales ($GWh$).
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.fact_generation_period`, `dw.dim_date`.
- **Formulas**: $\text{Loss Proxy (GWh)} = \text{Gross Generation} - \text{Billed Sales}$, $\text{Loss \%} = \frac{\text{Loss}}{\text{Gross Generation}} \times 100\%$.

### [Q23: Data Quality Anomaly Categorization & Quarantine Audit Trail](../../database/queries/phase3/member_06_grid_efficiency/Q23.sql)
- **Business Question**: What types of data-quality problems were detected during the historical data integration process, and what were the quarantine rates?
- **Relevance**: Provides transparency into data-cleaning gates, verifying that corrupt, negative, or unmapped telemetry records were isolated without contaminating warehouse facts.
- **Academic Lecture Mapping**: Lecture 6 (Data Preprocessing: Noise, Outlier & Quarantine Isolation), Lecture 8 (Multilevel Summaries using GROUPING SETS).
- **Fact Grain**: Aggregated issue occurrences across historical pipeline execution batches.
- **Tables Consulted**: `audit.data_quality_issue`, `audit.etl_run`.
- **Formulas**: $\text{Issue Share \%} = \frac{\text{Count}(\text{issue\_id})}{\text{Total Issues}} \times 100\%$.

### [Q24: ETL Pipeline Execution Performance, Throughput & End-to-End Data Lineage](../../database/queries/phase3/member_06_grid_efficiency/Q24.sql)
- **Business Question**: How effectively did the historical data ingestion pipeline process, validate and load records, and what was the end-to-end audit lineage?
- **Relevance**: Proves warehouse operational efficiency, SLA compliance, and regulatory traceability from immutable raw files down to dimensional fact primary keys.
- **Academic Lecture Mapping**: Lecture 4 (ETL Process Monitoring, Batch Scheduling & Throughput), Lecture 6 (Audit Trail, Provenance & Lineage Maintenance).
- **Fact Grain**: Pipeline batch run and target dimensional table lineage count.
- **Tables Consulted**: `audit.etl_run`, `audit.record_lineage`.
- **Formulas**: $\text{Throughput} = \frac{\text{Rows Read}}{\Delta t\text{ (seconds)}}$, $\text{Quarantine Rate \%} = \frac{\text{Rows Quarantined}}{\text{Rows Read}} \times 100\%$.
