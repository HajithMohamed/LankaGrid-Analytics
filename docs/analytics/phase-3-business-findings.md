# Phase 3 Key Business Findings & Grid Analytics Insights
## GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka

This report synthesizes the core findings and numerical insights produced by the GridLens analytical engine across the 24 business queries. All metrics originate directly from executed SQL queries over authentic historical datasets.

---

## 1. Generation Mix and Renewable Penetration (Member 1)

1. **March 2024 Generation Mix (Q01)**:
   - Total national dispatched electrical energy in March 2024 was **1,399,337.00 MWh** (~1.40 TWh).
   - **Thermal Coal (Lakvijaya Units 1–3)** provided the largest single source of electrical energy: **595,524.50 MWh (42.56%)**.
   - **Thermal Oil (Heavy Fuel Oil & Diesel)** contributed **387,450.75 MWh (27.69%)**, demonstrating substantial ongoing dependence on imported fossil fuels during dry pre-monsoon conditions.
   - **Major Hydro** supplied **321,595.50 MWh (22.98%)**.
   - Non-conventional renewable energy (NCRE) contributed:
     - Mini Hydro: **40,313.75 MWh (2.88%)**
     - Utility Solar PV: **22,839.50 MWh (1.63%)**
     - Wind (Thambapavani & SPP): **19,848.00 MWh (1.42%)**
     - Biomass: **11,765.00 MWh (0.84%)**

2. **Daily Renewable Penetration Variability (Q02)**:
   - Total renewable generation (Major Hydro + Mini Hydro + Solar + Wind + Biomass) averaged **29.75%** across March 2024.
   - Daily renewable penetration varied between a low of **27.13%** (on March 18) and a high of **34.68%** (on March 31).
   - The primary driver of renewable fluctuation was major hydro dispatch modulation rather than solar or wind variability.

3. **Power Plant Capacity Factor & Utilization Analysis (Q03)**:
   - Lakvijaya Coal units operated as steady baseload with capacity factors of **88.74% to 89.15%** (peak utilization 94.74%–97.60%).
   - Combined cycle thermal oil (Kelanitissa CC) maintained an **82.43%** capacity factor.
   - Major hydro stations were modulated for peaking duty and water conservation: Victoria operated at **38.15%** capacity factor, Samanalawewa at **56.01%**, and Kotmale at **12.21%**.
   - Stations where observed peak dispatch exceeds reference baseline ratings (Polpitiya 87.0 MW peak vs 75.0 MW; West Coast 289.0 MW peak vs 270.0 MW; Victoria 220.0 MW peak vs 210.0 MW) are recorded as observed dispatch exceedances against reference registries, noting that verification of physical plant repowering or high-head conditions requires further technical commissioning records.

4. **Time-of-Use Peaking Contribution (Q04)**:
   - During the **Evening Peak (18:30–22:30)**, major hydro generation surged to **32.40%** of total generation, compared to 20.95% during the Daytime (05:30–18:30).
   - Solar contribution dropped to **0.00%** during the evening peak, highlighting the necessity of hydro and thermal oil fast-start capacity.

---

## 2. Grid Dispatch Dynamics and Operational Ramping (Member 2)

1. **Diurnal Load Curves: Weekday vs Weekend (Q05)**:
   - Average weekday system demand peaked at **2,476.32 MW** at Slot 77 (19:15), with a secondary daytime plateau averaging **2,150–2,280 MW**.
   - Weekend demand peaked lower at **2,241.18 MW** (a **9.50% reduction**), reflecting commercial and industrial closures.
   - Baseload night trough (03:00–04:30) averaged **1,280–1,340 MW** on both weekdays and weekends.

2. **Ramping Rates and Operational Stress (Q06)**:
   - The grid experiences its steepest positive ramping stress systematically at **Slot 75 (18:30–18:45)**.
   - The maximum observed 15-minute system upward ramp reached **+141.00 MW** (+9.40 MW/min) on Sunday, March 17, 2024 (Interval 75, 18:30–18:45), driven by the sharp evening lighting demand surge.
   - The steepest downward ramp occurred at **Slot 92 (22:45–23:00)** with a drop of **-122.40 MW** (-8.16 MW/min).

3. **Baseload vs Peaking Plant Classification (Q07)**:
   - **Lakvijaya Coal** maintained an availability factor of **100.0%** and a coefficient of variation ($CV$) of **0.09**, confirming its role as primary baseload.
   - **Kotmale** ($CV = 0.94$, 43.8% availability) and **Upper Kotmale** ($CV = 1.39$, 23.7% availability) exhibited high volatility, confirming designated peaking duty.

4. **Telemetry-to-Published-Energy Reconciliation (Q08)**:
   - On the March 1, 2024 baseline day, discrete 15-minute Riemann integration of transmission SCADA telemetry totaled **46,308.00 MWh**, compared to **48,223.00 MWh** from official PUCSL settlement records (`15-Minutes-Report-31-Mar2024.xlsx`, Sheet `01.03`, Col 98, Rows 41–48), establishing an authentic net variance of **1,915.00 MWh (3.97%)**.
   - The variance is overwhelmingly explained by untelemetered distributed sources:
     - Commercial utility & embedded rooftop solar: published **2,379.70 MWh** vs telemetered **651.50 MWh** (variance **+1,728.20 MWh**, 72.62%).
     - Embedded 33kV mini-hydro: published **1,896.80 MWh** vs telemetered **1,594.00 MWh** (variance **+302.80 MWh**, 15.96%).
   - Transmission-connected grid dispatch reconciles with extreme precision:
     - Major Hydro: published **10,375.60 MWh** vs telemetered **10,370.50 MWh** (variance **+5.10 MWh**, +0.05%).
     - Thermal Coal: published **19,493.00 MWh** vs telemetered **19,484.25 MWh** (variance **+8.75 MWh**, +0.04%).
     - Wind: published **1,502.40 MWh** vs telemetered **1,472.50 MWh** (variance **+29.90 MWh**, +1.99%).
     - Biomass: published **382.30 MWh** vs telemetered **389.75 MWh** (variance **-7.45 MWh**, -1.95%).
     - Thermal Oil: published **12,193.20 MWh** vs telemetered **12,345.50 MWh** (variance **-152.30 MWh**, -1.25%).

---

## 3. Electricity Demand & Customer Dynamics (Member 3)

1. **Five-Year Sectoral Trajectories (Q09 & Q10)**:
   - **Hotel Sector**: Rebounded dramatically from **193.00 GWh (2020)** to **355.00 GWh (2024)**, exhibiting **+83.94% net growth** and a **CAGR of +16.46%**, tracking the post-pandemic revival of Sri Lanka's tourism industry.
   - **Domestic Consumption**: Contracted from **5,090.00 GWh (2020)** to **4,701.00 GWh (2024)** (**-7.64% net change**, **CAGR of -1.97%**), driven by steep tariff revisions in August 2022 and February 2023 alongside distributed rooftop solar adoption.
   - **Industrial Consumption**: Grew from **4,164.00 GWh (2020)** to **4,622.00 GWh (2024)** (**+11.00% net gain**, **CAGR of +2.64%**).
   - **General Purpose (Commercial)**: Expanded from **2,837.00 GWh (2020)** to **3,472.00 GWh (2024)** (**+22.38%**, **CAGR of +5.18%**).

2. **Structural Composition Shifts & Average Consumption (Q11)**:
   - Domestic demand share fell from **35.63% (2020)** to **30.95% (2024)** of total national billed sales.
   - Productive economic sectors (Industrial + Commercial + Hotel + Agriculture) increased their combined share from **50.35% (2020)** to **55.64% (2024)**.
   - Domestic average consumption dropped from 71.3 kWh/account/month in 2021 to 62.4 kWh/account/month in 2023 following tariff restructuring.

3. **CEB Retail vs LECO Bulk Supply (Q12)**:
   - LECO bulk purchases remained stable between **1,539.00 GWh and 1,633.00 GWh annually**, consistently accounting for **10.67% to 11.23%** of national electricity sales.

---

## 4. Weather and Renewable Resource Coupling (Member 4)

1. **Climatic Solar Irradiance Profiles (Q13)**:
   - Northern dry zone (`LOC_MANNAR_WIND`) recorded a 5-year average Global Horizontal Irradiance of **18.57 MJ/m²/day** (**5.16 Peak Sun Hours/day**).
   - Central hydro catchment (`LOC_VICTORIA_CATCHMENT`) recorded an average of **18.31 MJ/m²/day** (**5.09 Peak Sun Hours/day**).
   - Both stations exhibit clear pre-monsoon solar peaks in March–April (5.8–6.4 PSH/day) and cloud-induced depressions during the Southwest Monsoon (June–July).

2. **Empirical Temperature vs Grid Demand Correlation (Q14)**:
   - Paired daily observations across March 2024 revealed an empirical Pearson correlation of **$r = +0.0083$** between two-station mean ambient temperature (`LOC_VICTORIA_CATCHMENT` and `LOC_MANNAR_WIND`) and peak dispatch MW, confirming near-zero coupling at these specific non-urban monitoring nodes.
   - The two-station mean temperature exhibits a mild positive correlation with total daily electrical energy (**$r = +0.1248$**) across the 31 paired March days, reflecting seasonal daytime thermal demand across the pre-monsoon dry season.

3. **Precipitation Seasonality & Monsoon CUBE Dynamics (Q15)**:
   - The multi-dimensional cube over 1,827 days revealed a 5-year total rainfall of **16,929.50 mm** across the two nodes.
   - Central catchment (`LOC_VICTORIA_CATCHMENT`) captured **10,757.20 mm (63.54%)**, driven heavily by Second Inter-Monsoon (October–November, 3,421.10 mm) and Northeast Monsoon rains.
   - Mannar captured **6,172.30 mm (36.46%)** with sharp semi-arid seasonality.

4. **Wind Resource Coupling (Q16)**:
   - Mean 50m hub-height wind speed at Mannar during March 2024 was **5.37 m/s** (ranging from 2.90 to 7.73 m/s).
   - The Pearson correlation between NASA POWER 50m wind speed and utility-scale dispatched wind energy was **$r = +0.7143$** ($r(v^3) = +0.7132$), demonstrating strong physical coupling between satellite reanalysis wind fields and grid telemetry.

---

## 5. Plant Operations & Capacity Performance (Member 5)

1. **Online Availability & Duty Cycles (Q17)**:
   - Lakvijaya Units 1, 2, and 3 operated with **100.0% duty cycle** (2,976 out of 2,976 fifteen-minute intervals online).
   - Peaking hydro stations were dispatched selectively: Victoria was online for 96.2% of intervals (modulating power), while Bowatenna was dispatched for only 8.5% of intervals.

2. **Observed Peak Dispatch vs Rated Nameplate Capacity (Q18)**:
   - 10 stations delivered $\ge 95\%$ of their rated reference nameplate capacities during March 2024.
   - Stations where observed peak dispatch exceeded reference nameplate rating (Polpitiya **116.0% peak ratio**, 87.0 MW observed vs 75.0 MW reference; West Coast Yugadanavi **107.0%**, 289.0 MW observed vs 270.0 MW reference; Victoria Hydro **104.8%**, 220.0 MW observed vs 210.0 MW reference; Samanalawewa **101.7%**, 122.0 MW observed vs 120.0 MW reference; New Laxapana **101.0%**, 101.0 MW observed vs 100.0 MW reference; Randenigala **100.8%**, 123.0 MW observed vs 122.0 MW reference) are systematically catalogued with status `OBSERVED PEAK EXCEEDS REFERENCE NAMEPLATE (FURTHER EVIDENCE REQUIRED)`. These empirical exceedances reflect telemetry observations against reference registries, and any underlying physical factors (such as plant repowering, high hydraulic head, or plant overload margins) require secondary engineering documentation.
   - Kelanitissa Gas Turbine 7 recorded zero dispatch during March 2024, catalogued as `ZERO RECORDED DISPATCH (RESERVE STANDBY OR OUTAGE)` (0 MW observed peak vs 115.0 MW rated).

3. **Lakvijaya Unit Baseload Continuity (Q19)**:
   - Lakvijaya Unit 1 generated **198,478.00 MWh**, Unit 2 generated **198,973.00 MWh**, and Unit 3 generated **198,073.50 MWh**, totaling **595,524.50 MWh** with zero forced outages.

4. **Evening Peak Merit-Order Contribution (Q20)**:
   - During the evening peak window (18:30–22:30), thermal coal provided **39.67%** of energy, major hydro provided **32.40%**, and thermal oil supplied **23.19%**.

---

## 6. Grid Efficiency, Reconciliation & Data Quality (Member 6)

1. **Five-Year Grid Sales Efficiency Trends (Q21)**:
   - Between 2020 and 2024, the productive economic share of national billed electricity consumption expanded steadily from **50.35% (7,194.00 GWh) in 2020** to **55.64% (8,452.50 GWh) in 2024**.
   - Residential consumption contracted from **35.63% (5,090.00 GWh) in 2020** to **30.95% (4,701.00 GWh) in 2024**, demonstrating positive economic structural transition and energy conservation following tariff reforms.

2. **Cross-Source Multi-Tier Loss Proxy Reconciliation (Q22)**:
   - Gross grid generation minus billed retail sales revealed a national transmission and distribution loss proxy of **8.8% to 9.6%** over the 5-year historical window (2020–2024), consistent with audited CEB regulatory filings.

3. **Data Quality Quarantine Audit Trail (Q23)**:
   - A total of **926 data quality issues** were logged across warehouse pipeline execution batches.
   - **879 issues (94.92%)** were unmatched dimension entities (`DQ_DIM_UNMATCHED_ENTITY`), isolated and mapped during dimension resolution.
   - **47 issues (5.08%)** were negative active power measurements (`DQ_GEN_NEGATIVE_OUTPUT`), quarantined from Barge plant telemetry.
   - All quarantine rules and subtotals reconcile to exactly **100.00%**.

4. **ETL Execution Performance, Throughput & Lineage (Q24)**:
   - The warehouse pipeline processed 273,452 raw source records across 4 automated loaders.
   - `pucsl_dispatch_loader`: 228,960 rows read, 217,816 inserted, 815 quarantined (0.36% quarantine rate), average throughput **405.3 rows/sec**.
   - `nasa_weather_loader`: 44,220 rows read, 21,924 inserted, 0 quarantined, throughput **532.3 rows/sec**.
   - 228,145 audit lineage records were verified in `audit.record_lineage`, guaranteeing end-to-end regulatory traceability.
