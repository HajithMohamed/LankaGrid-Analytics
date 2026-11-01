# Phase 3 Analytical Query Catalogue (Q01–Q24)
## GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka

This catalogue documents all 24 analytical queries designed and implemented across six engineering team members for **Phase 3 (Business Intelligence, Advanced OLAP, and Historical Data Analysis)**. Each query answers authentic grid operational, economic, or environmental business questions using verified historical data (2020–2024 CEB Sales, 2020–2024 NASA POWER Weather, and March 2024 PUCSL 15-Minute Dispatch).

---

## Member 1: Grid Generation Mix & Renewable Penetration

### [Q01: Generation Mix by Energy Source (March 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_01_generation/Q01.sql)
- **Business Question**: What was the total energy generation (MWh and %) by energy source and fuel type for March 2024?
- **Relevance**: Evaluates national dependency on fossil fuels vs. clean renewables and validates fuel diversification strategies.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Roll-Up from plant to fuel type to major category; Star Schema dimension joins).
- **Fact Grain**: 15-minute power plant active power dispatch ($MW$). Derived energy ($MWh = MW \times 0.25h$).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $\text{Energy MWh} = \sum(\text{active\_power\_mw} \times 0.25)$, $\text{Share \%} = \frac{\text{Category MWh}}{\text{Total MWh}} \times 100\%$.

### [Q02: Daily Renewable vs Non-Renewable Penetration (March 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_01_generation/Q02.sql)
- **Business Question**: How did the renewable energy penetration percentage vary daily across March 2024?
- **Relevance**: Analyzes daily grid variability and tracks progress toward Sri Lanka's policy target of 70% renewable generation by 2030.
- **Academic Lecture Mapping**: Lecture 1 (Time-Variant Historical Analysis), Lecture 5 (Daily Timeseries KPI Aggregation).
- **Fact Grain**: Daily energy aggregation by renewable classification.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_energy_source`, `dw.dim_date`.
- **Formulas**: $\text{Renewable \%} = \frac{\sum \text{MWh}_{\text{renewable}}}{\sum \text{MWh}_{\text{total}}} \times 100\%$.

### [Q03: Plant Capacity Factor Analysis (March 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_01_generation/Q03.sql)
- **Business Question**: What is the realized capacity factor for major generation plants relative to rated nameplate capacity?
- **Relevance**: Identifies plant utilization efficiency, underperforming thermal or hydro assets, and baseload availability.
- **Academic Lecture Mapping**: Lecture 3 & 4 (Fact Constellation: joining plant nameplate capacity with operational dispatch facts).
- **Fact Grain**: Monthly aggregate plant energy vs. maximum theoretical potential ($P_{\text{rated}} \times 744\text{ hours}$).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `ref.seed_power_plant_registry`.
- **Formulas**: $\text{Capacity Factor \%} = \frac{\text{Actual Generation (MWh)}}{\text{Installed Capacity (MW)} \times 744\text{ hours}} \times 100\%$.

### [Q04: Peak vs Off-Peak Generation Contribution (March 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_01_generation/Q04.sql)
- **Business Question**: How does each generation source contribute to Day, Peak, and Off-Peak Time-of-Use (TOU) windows?
- **Relevance**: Measures peaking capability and identifies which thermal or hydro assets meet the expensive 18:30–22:30 evening demand surge.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Slicing by Time-of-Use regime), Lecture 8 (Multi-Dimensional GROUPING SETS).
- **Fact Grain**: 15-minute interval dispatch classified by TOU tariff bucket.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_interval`, `dw.dim_energy_source`.
- **Formulas**: Pivot/crosstab aggregation using conditional `FILTER (WHERE di.tou_regime = 'PEAK')`.

---

## Member 2: Grid Dispatch Dynamics & 15-Minute Load Profiles

### [Q05: 15-Minute Diurnal Dispatch Curves — Weekday vs Weekend](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_02_dispatch/Q05.sql)
- **Business Question**: What is the average 24-hour diurnal dispatch curve for weekdays compared to weekends across March 2024?
- **Relevance**: Determines base, intermediate, and peak loading cycles, revealing industrial shutdown effects on weekend load profiles.
- **Academic Lecture Mapping**: Lecture 2 (Slice and Dice across calendar type dimension `is_weekend`), Lecture 5 (Diurnal Load Profiling).
- **Fact Grain**: 15-minute interval slot (1 to 96) averaged across calendar day types.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_interval`, `dw.dim_date`.
- **Formulas**: $\overline{P}_{\text{slot}} = \text{AVG}(\sum_{\text{plants}} \text{active\_power\_mw})$.

### [Q06: 15-Minute Dispatch Ramp Rate Analysis](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_02_dispatch/Q06.sql)
- **Business Question**: What are the steepest 15-minute positive and negative grid ramp rates (MW/interval and MW/min)?
- **Relevance**: Informs grid operators of ramping stress, fast-start hydro spinning reserve requirements, and solar sunset drop-offs.
- **Academic Lecture Mapping**: Lecture 5 (Analytical Window Functions `LAG()` ordered by temporal sequence).
- **Fact Grain**: 15-minute system dispatch timestamp delta.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_interval`, `dw.dim_date`.
- **Formulas**: $\Delta P = P_t - P_{t-1}$, $\text{Ramp Rate (MW/min)} = \frac{\Delta P}{15}$.

### [Q07: Baseload vs Peaking Plant Operational Behavior](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_02_dispatch/Q07.sql)
- **Business Question**: Which power plants operate continuously as baseload assets versus cycling/peaking assets?
- **Relevance**: Characterizes plant duty cycles (baseload vs. load-following vs. peaking) using operational availability and coefficient of variation ($CV$).
- **Academic Lecture Mapping**: Lecture 5 (Descriptive Statistics: Standard Deviation, Mean, and Relative Dispersion $CV$).
- **Fact Grain**: Plant-level 15-minute dispatch across 2,976 intervals in March 2024.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`.
- **Formulas**: $CV = \frac{\sigma}{\mu}$, $\text{Duty Cycle} = \text{CASE WHEN } \text{Active \%} \ge 90\% \text{ THEN 'Baseload' ...}$.

### [Q08: Dispatch Telemetry vs Published Daily Generation Reconciliation](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_02_dispatch/Q08.sql)
- **Business Question**: How closely does integrated 15-minute telemetry reconcile with daily published operational generation reports?
- **Relevance**: Audits telemetry data pipeline accuracy against official published utility statistics, identifying unmetered auxiliary losses.
- **Academic Lecture Mapping**: Lecture 6 (Source Conflict Resolution and Multi-Source Reconciliation).
- **Fact Grain**: Daily energy generation comparison by major power station.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.fact_generation_period`, `dw.dim_power_plant`, `dw.dim_date`.
- **Formulas**: $\text{Variance \%} = \frac{\text{Telemetry MWh} - \text{Published MWh}}{\text{Published MWh}} \times 100\%$.

---

## Member 3: Sectoral Electricity Sales & Demand Dynamics

### [Q09: Five-Year Sectoral Electricity Sales Trends (2020–2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_03_sales/Q09.sql)
- **Business Question**: How did electricity sales change across consumer categories from 2020 to 2024?
- **Relevance**: Evaluates national electricity demand trajectories through the COVID-19 pandemic, 2022 economic crisis, and tariff hikes.
- **Academic Lecture Mapping**: Lecture 1 (Historical Non-Volatile Warehouse Storage), Lecture 5 (Window LAG() for YoY Growth).
- **Fact Grain**: Annual billed sales volume per consumption sector.
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\text{YoY Growth \%} = \frac{S_t - S_{t-1}}{S_{t-1}} \times 100\%$.

### [Q10: Compound Annual Growth Rate (CAGR) by Sector (2020–2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_03_sales/Q10.sql)
- **Business Question**: What was the 4-year Compound Annual Growth Rate (CAGR) for each consumer category?
- **Relevance**: Provides annualized medium-term growth benchmarks for capacity expansion planning and long-term transmission modeling.
- **Academic Lecture Mapping**: Lecture 5 (Mathematical Modeling and Exponential Window Aggregation).
- **Fact Grain**: Sectoral sales endpoints (2020 base year to 2024 end year).
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\text{CAGR} = \left(\frac{S_{2024}}{S_{2020}}\right)^{\frac{1}{4}} - 1$.

### [Q11: Sectoral Sales Shift and Structural Mix (2020 vs 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_03_sales/Q11.sql)
- **Business Question**: How has the structural composition of electricity sales shifted between pre-crisis (2020) and recovery (2024)?
- **Relevance**: Measures macroeconomic structural transformations, such as the growth in tourism/hospitality vs. contraction in domestic demand.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Comparative Slice between 2020 and 2024), Lecture 8 (Structural Percentage Decomposition).
- **Fact Grain**: Category market share percentage across milestone years.
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\Delta \text{Share (pp)} = \text{Share}_{2024} - \text{Share}_{2020}$.

### [Q12: CEB Retail vs LECO Bulk Supply Reconciliation (2020–2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_03_sales/Q12.sql)
- **Business Question**: What proportion of national electricity sales was distributed directly by CEB versus LECO bulk supply?
- **Relevance**: Details the distribution split between CEB direct customer retail areas and LECO coastal franchise areas.
- **Academic Lecture Mapping**: Lecture 6 (Non-Double Counting: separating LECO bulk resale from CEB direct retail).
- **Fact Grain**: Annual sales split between CEB retail and LECO bulk supply.
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.dim_consumption_sector`, `dw.dim_date`.
- **Formulas**: $\text{LECO Share \%} = \frac{\text{LECO GWh}}{\text{National Total GWh}} \times 100\%$.

---

## Member 4: Weather Impacts & Renewable Resource Correlation

### [Q13: Five-Year Solar Irradiance Profiles Across Climate Zones](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_04_weather/Q13.sql)
- **Business Question**: How does daily and monthly solar irradiance (GHI) vary across Sri Lanka's climatic zones (Central Hydro vs Dry Zone Solar)?
- **Relevance**: Identifies optimal geographical locations for utility-scale solar PV development and quantifies seasonal monsoon cloud attenuation.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Roll-Up from daily weather observations to monthly/annual geographic aggregations).
- **Fact Grain**: Daily meteorological observations across 12 distinct geographic nodes (2020–2024).
- **Tables Consulted**: `dw.fact_weather_daily`, `dw.dim_weather_location`, `dw.dim_date`.
- **Formulas**: $\text{Peak Sun Hours (PSH)} = \frac{\text{GHI (MJ/m}^2\text{/day)}}{3.6}$.

### [Q14: Correlation Between Temperature and Peak Electricity Demand](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_04_weather/Q14.sql)
- **Business Question**: Does higher ambient temperature in urban centers correlate with increased grid peak electricity demand?
- **Relevance**: Quantifies the cooling-degree sensitivity (air conditioning load) on Sri Lanka's electricity grid during the hot pre-monsoon month.
- **Academic Lecture Mapping**: Lecture 5 (Statistical Correlation Analysis using `CORR()`, Covariance, and Linear Regression slopes).
- **Fact Grain**: Daily maximum grid demand ($MW$) paired with daily maximum temperature ($^\circ C$) in Colombo.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.fact_weather_daily`, `dw.dim_weather_location`, `dw.dim_date`.
- **Formulas**: Pearson correlation coefficient $r = \frac{\sum (T - \overline{T})(P - \overline{P})}{\sqrt{\sum(T-\overline{T})^2 \sum(P-\overline{P})^2}}$.

### [Q15: Monthly Wind Speed Distribution Across Renewable Corridors](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_04_weather/Q15.sql)
- **Business Question**: What are the seasonal wind speed profiles and Weibull-proxy metrics at major wind development sites (Mannar vs Kalpitiya)?
- **Relevance**: Evaluates commercial feasibility and seasonal wind power output, which surges during the Southwest monsoon (May–September).
- **Academic Lecture Mapping**: Lecture 2 (OLAP Slice on Wind Metric and Drill-Down by Geographic Coordinate), Lecture 5 (Statistical Dispersion).
- **Fact Grain**: Daily average wind speed at 10m and 50m hub heights across 5 years.
- **Tables Consulted**: `dw.fact_weather_daily`, `dw.dim_weather_location`, `dw.dim_date`.
- **Formulas**: $\overline{v}_{\text{monthly}} = \text{AVG}(\text{wind\_speed\_50m})$, $\text{Estimated Power Density} \propto v^3$.

### [Q16: Thambapavani Wind Dispatch vs Mannar Wind Speed Correlation](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_04_weather/Q16.sql)
- **Business Question**: How strongly does actual daily generation from Thambapavani Wind Farm correlate with NASA POWER 50m wind speed in Mannar?
- **Relevance**: Validates satellite meteorological datasets against real utility-scale wind plant generation, verifying NASA POWER for resource modeling.
- **Academic Lecture Mapping**: Lecture 4 (Fact-to-Fact Join across Conformed Date Dimension), Lecture 5 (Bivariate Correlation).
- **Fact Grain**: Daily energy output ($MWh$) joined with daily mean wind speed ($m/s$) for March 2024.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.fact_weather_daily`, `dw.dim_power_plant`, `dw.dim_weather_location`, `dw.dim_date`.
- **Formulas**: $r(\text{Generation}_{\text{MWh}}, \text{WindSpeed}_{\text{50m}}) = \text{CORR}(y, x)$.

---

## Member 5: Power Plant Performance & Operational Efficiency

### [Q17: Lakvijaya Coal Plant Basal Loading & Outage Analysis](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_05_plant_operations/Q17.sql)
- **Business Question**: What was the hourly loading profile, minimum stable generation, and operational stability of Lakvijaya Coal Plant?
- **Relevance**: Evaluates the stability of Sri Lanka's largest and lowest-cost thermal baseload facility (900 MW nameplate).
- **Academic Lecture Mapping**: Lecture 5 (Operational Time-Series Analysis, Outage Interval Detection via Conditional Aggregations).
- **Fact Grain**: Daily 15-minute dispatch aggregated across Lakvijaya Coal units.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_date`.
- **Formulas**: $\text{Daily Energy} = \sum \text{MWh}$, $\text{Max MW} = \max(P)$, $\text{Min MW} = \min(P)$, $\text{Loading Ratio} = \frac{\overline{P}}{P_{\text{rated}}}$.

### [Q18: Major Hydro Complex Capacity Utilization (March 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_05_plant_operations/Q18.sql)
- **Business Question**: How were major hydro complexes (Mahaweli and Laxapana cascades) dispatched during the dry pre-monsoon month?
- **Relevance**: Assesses water-energy nexus management, reservoir conservation strategies, and hydro availability before the monsoon rains.
- **Academic Lecture Mapping**: Lecture 2 (Hierarchy Roll-Up from individual hydro plant to river cascade complex).
- **Fact Grain**: Monthly cascade generation totals vs. installed cascade capacity.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`.
- **Formulas**: $\text{Cascade MWh} = \sum_{\text{plants } \in \text{ cascade}} \text{MWh}$, $\text{Utilization \%} = \frac{\text{Cascade MWh}}{\text{Installed MW} \times 744\text{h}} \times 100\%$.

### [Q19: Thermal Oil Generation Dispatch Heat Map by Plant & Hour](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_05_plant_operations/Q19.sql)
- **Business Question**: During which hours of the day are expensive oil-fired thermal plants (Kelanitissa, West Coast, Barge) dispatched?
- **Relevance**: Analyzes fuel costs and merit-order dispatch behavior, showing when expensive diesel/furnace oil is required to prevent deficits.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Matrix / Heat Map Construction using CROSSTAB or 2D GROUP BY).
- **Fact Grain**: Average dispatched active power ($MW$) by thermal plant and hour of day (0 to 23).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_interval`.
- **Formulas**: $\overline{P}_{\text{plant, hour}} = \text{AVG}(\text{active\_power\_mw})$.

### [Q20: Plant Peaking Duty Index (Evening Peak vs Daytime)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_05_plant_operations/Q20.sql)
- **Business Question**: Which generation facilities serve predominantly as peaking plants rather than round-the-clock baseload?
- **Relevance**: Classifies plants by flexibility and fast-ramping capability required during evening peak hours.
- **Academic Lecture Mapping**: Lecture 5 (Ratio Analysis and Index Construction).
- **Fact Grain**: Ratio of mean power during Evening Peak (18:30–22:30) to mean power during Daytime (05:30–18:30).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_interval`.
- **Formulas**: $\text{Peaking Duty Index} = \frac{\overline{P}_{\text{Peak}}}{\overline{P}_{\text{Daytime}}}$.

---

## Member 6: Grid Reliability, Transmission Efficiency & Environmental Impact

### [Q21: Estimated Carbon Emissions by Energy Source (March 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_06_grid_efficiency/Q21.sql)
- **Business Question**: What was the total estimated greenhouse gas footprint ($tCO_2e$) and grid carbon intensity ($gCO_2/kWh$)?
- **Relevance**: Quantifies environmental impact and provides carbon accounting for national climate reporting and carbon offset programs.
- **Academic Lecture Mapping**: Lecture 4 (Fact Dimension Joining with Environmental Reference Seed Multipliers).
- **Fact Grain**: Monthly carbon emissions calculated by fuel combustion factors.
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_energy_source`, `ref.seed_environmental_emission_factors`.
- **Formulas**: $\text{Emissions } (tCO_2e) = \sum \left(\text{MWh} \times \text{Factor } \frac{tCO_2}{MWh}\right)$, $\text{Grid Intensity} = \frac{\text{Total Emissions } (g)}{\text{Total Generation } (kWh)}$.

### [Q22: Thermal Generation Fuel Cost Proxy Analysis (March 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_06_grid_efficiency/Q22.sql)
- **Business Question**: What was the estimated fuel cost incurred by each thermal power plant and fuel category during March 2024?
- **Relevance**: Demonstrates economic merit order, showing that oil plants account for a disproportionate share of operating expenditure.
- **Academic Lecture Mapping**: Lecture 2 (OLAP Cost Roll-Up), Lecture 5 (Financial Metric Modeling).
- **Fact Grain**: Plant-level monthly fuel cost ($LKR$).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_power_plant`, `dw.dim_energy_source`.
- **Formulas**: $\text{Fuel Cost (LKR)} = \text{MWh} \times \text{Specific Fuel Cost (LKR/kWh)} \times 1{,}000$.

### [Q23: System Minimum-to-Maximum Load Ratio (March 2024)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_06_grid_efficiency/Q23.sql)
- **Business Question**: What was the daily peak-to-trough demand ratio and load factor on the Sri Lankan transmission network?
- **Relevance**: Measures grid operational efficiency and the requirement for flexible cycling generation.
- **Academic Lecture Mapping**: Lecture 5 (Extreme Value Ratios, Min/Max Dispersion, and Grid Load Factor).
- **Fact Grain**: Daily grid minimum demand ($MW$), peak demand ($MW$), and average demand ($MW$).
- **Tables Consulted**: `dw.fact_dispatch_interval`, `dw.dim_date`.
- **Formulas**: $\text{Load Factor \%} = \frac{\overline{P}_{\text{daily}}}{P_{\text{peak}}} \times 100\%$, $\text{Trough-to-Peak Ratio \%} = \frac{P_{\text{min}}}{P_{\text{peak}}} \times 100\%$.

### [Q24: Five-Year National Transmission and Distribution Loss Proxy](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/queries/phase3/member_06_grid_efficiency/Q24.sql)
- **Business Question**: What was the annual gap between total gross generated electricity and billed final consumption from 2020 to 2024?
- **Relevance**: Evaluates national transmission and distribution (T&D) loss trends and system efficiency improvements.
- **Academic Lecture Mapping**: Lecture 1 & 4 (Cross-Process Constellation Reconciliation between Generation and Sales).
- **Fact Grain**: Annual gross generation ($GWh$) vs. billed retail sales ($GWh$).
- **Tables Consulted**: `dw.fact_electricity_sales`, `dw.fact_published_statistic`, `dw.dim_date`.
- **Formulas**: $\text{Loss Proxy (GWh)} = \text{Gross Generation} - \text{Billed Sales}$, $\text{Loss \%} = \frac{\text{Loss}}{\text{Gross Generation}} \times 100\%$.

