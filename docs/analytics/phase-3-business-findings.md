# Phase 3 Key Business Findings & Grid Analytics Insights
## GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka

This report synthesizes the core findings and numerical insights produced by the GridLens analytical engine across the 24 business queries. All metrics originate directly from executed SQL queries over authentic historical datasets.

---

## 1. Generation Mix and Renewable Penetration (Member 1)

1. **March 2024 Generation Mix (Q01)**:
   - Total national dispatched electrical energy in March 2024 was **1,399,337.00 MWh** (~1.40 TWh).
   - **Thermal Coal (Lakvijaya)** provided the largest single source of electrical energy: **595,502.50 MWh (42.56%)**.
   - **Thermal Oil (Heavy Fuel Oil & Diesel)** contributed **387,489.25 MWh (27.69%)**, demonstrating substantial ongoing dependence on imported fossil fuels during dry pre-monsoon conditions.
   - **Major Hydro** supplied **321,570.00 MWh (22.98%)**.
   - Non-conventional renewable energy (NCRE) contributed:
     - Mini Hydro: **40,248.50 MWh (2.88%)**
     - Utility Solar: **22,763.50 MWh (1.63%)**
     - Wind (Thambapavani): **19,836.75 MWh (1.42%)**
     - Biomass: **11,926.50 MWh (0.84%)**

2. **Daily Renewable Penetration Variability (Q02)**:
   - Total renewable generation (Major Hydro + Mini Hydro + Solar + Wind + Biomass) averaged **29.75%** across March 2024.
   - Daily renewable penetration varied between a low of **27.13%** (on March 18) and a high of **34.68%** (on March 31).
   - The primary driver of renewable fluctuation was major hydro dispatch modulation rather than solar or wind variability.

3. **Time-of-Use Peaking Contribution (Q04)**:
   - During the **Evening Peak (18:30–22:30)**, major hydro generation surged to **32.40%** of total generation, compared to 20.95% during the Daytime (05:30–18:30).
   - Solar contribution dropped to **0.00%** during the evening peak, highlighting the necessity of hydro and thermal oil fast-start capacity.

---

## 2. Grid Dispatch Dynamics and Ramping Stress (Member 2)

1. **Diurnal Load Curves: Weekday vs Weekend (Q05)**:
   - Average weekday system demand peaked at **2,476.32 MW** at Slot 77 (19:15), with a secondary daytime plateau averaging **2,150–2,280 MW**.
   - Weekend demand peaked lower at **2,241.18 MW** (a **9.5% reduction**), reflecting commercial and industrial closures.
   - Baseload night trough (03:00–04:30) averaged **1,280–1,340 MW** on both weekdays and weekends.

2. **Ramping Rates and Operational Stress (Q06)**:
   - The grid experiences its steepest positive ramping stress systematically at **Slot 75 (18:30–18:45)**.
   - The maximum observed 15-minute system upward ramp reached **+141.25 MW** (+9.42 MW/min) on March 12, driven by the simultaneous cessation of solar generation and the evening domestic lighting surge.
   - The steepest downward ramp occurred at **Slot 92 (22:45–23:00)** with a drop of **-122.40 MW** (-8.16 MW/min).

3. **Baseload vs Peaking Plant Classification (Q07)**:
   - **Lakvijaya Coal** maintained an availability factor of **99.8%** and a coefficient of variation ($CV$) of **0.14**, confirming its role as primary baseload.
   - **Kothmale** and **Victoria** hydro plants exhibited $CV > 0.85$ and availability between 35% and 55%, confirming designated peaking duty.

---

## 3. Sectoral Electricity Demand Dynamics (Member 3)

1. **Five-Year Sectoral Trajectories (Q09 & Q10)**:
   - **Hotel Sector**: Experienced the strongest growth between 2020 and 2024, rebounding from **268.08 GWh** in 2020 to **493.10 GWh** in 2024 (**+83.94% total growth**, **CAGR of 16.46%**), reflecting tourism sector recovery.
   - **Domestic Consumption**: Contracted from **5,442.27 GWh** (2020) to **5,026.31 GWh** (2024) (**-7.64%**, **CAGR of -1.97%**), driven by steep tariff revisions in August 2022 and February 2023, coupled with rapid adoption of unmetered rooftop solar PV.
   - **Industrial Consumption**: Remained flat to slightly growing (**CAGR of +0.81%**), transitioning from 4,375.40 GWh (2020) to 4,519.82 GWh (2024).

2. **Structural Composition Shifts (Q11)**:
   - Domestic demand share fell by **3.1 percentage points** (from 37.8% of national sales in 2020 to 34.7% in 2024).
   - Commercial and hotel sectors increased their combined share from 21.2% to 24.5%.

3. **CEB Retail vs LECO Bulk Supply (Q12)**:
   - LECO bulk purchases remained stable between **1,520 GWh and 1,640 GWh annually**, representing **10.7% to 11.2%** of total national electricity sales.

---

## 4. Weather and Renewable Correlations (Member 4)

1. **Climatic Solar Irradiance Profiles (Q13)**:
   - Northern and Eastern dry zones (Mannar, Hambantota) recorded annual average Global Horizontal Irradiance (GHI) of **19.2 to 19.8 MJ/m²/day** (**5.33 to 5.50 Peak Sun Hours/day**).
   - Central hydro catchment areas (Victoria, Nuwara Eliya) recorded **18.4 to 18.9 MJ/m²/day** (**5.11 to 5.25 PSH/day**), showing significant monsoon cloud depression in June–July and October–November.

2. **Wind Resource and Generation Correlation (Q15 & Q16)**:
   - Mean 50m hub-height wind speed at Mannar during March 2024 was **6.12 m/s**.
   - The Pearson correlation between NASA POWER 50m wind speed and Thambapavani 100 MW Wind Farm daily generation was **r = +0.7143** ($R^2 = 0.5102$), confirming strong physical coupling between satellite reanalysis wind fields and utility-scale output.

3. **Temperature Sensitivity (Q14)**:
   - Colombo ambient maximum temperature and national daytime peak demand showed a positive correlation of **r = +0.5821**, indicating an estimated sensitivity of **~38 MW per °C** during pre-monsoon daytime conditions.

---

## 5. Plant Operations and Cascade Dispatch (Member 5)

1. **Lakvijaya Coal Operations (Q17)**:
   - Operates across three 300 MW units with average total output of **800.41 MW** and maximum output of **884.20 MW**.
   - No complete plant outages occurred during March 2024; loading remained above 650 MW continuously.

2. **Hydro Cascade Management (Q18)**:
   - Mahaweli Cascade (Victoria, Randenigala, Rantembe, Kothmale, Bowatenna, Ukuwela) delivered **214,890.50 MWh**.
   - Laxapana Cascade (New Laxapana, Old Laxapana, Polpitiya, Wimalasurendra, Canyon) delivered **106,679.50 MWh**.
   - Overall cascade capacity factor was **26.8%**, reflecting deliberate water conservation for the upcoming dry inter-monsoon period.

3. **Peaking Duty Index (Q20)**:
   - Victoria Hydro had a Peaking Duty Index of **1.62** ($\overline{P}_{\text{Peak}} = 142.3\text{ MW}$ vs $\overline{P}_{\text{Day}} = 87.8\text{ MW}$).
   - Kothmale Hydro had an index of **1.48**.
   - Baseload Lakvijaya had an index of **1.03**, confirming flat round-the-clock dispatch.

---

## 6. Grid Efficiency and Environmental Metrics (Member 6)

1. **Grid Carbon Emissions (Q21)**:
   - Total March 2024 greenhouse gas emissions from electricity generation were estimated at **852,431.25 tCO₂e**.
   - Lakvijaya Coal contributed **565,727.38 tCO₂e (66.37%)** due to coal's emission factor ($0.95\text{ tCO}_2\text{/MWh}$).
   - Thermal oil contributed **286,703.88 tCO₂e (33.63%)**.
   - National grid carbon intensity averaged **609.17 gCO₂/kWh**.

2. **Thermal Fuel Expenditure (Q22)**:
   - Total estimated thermal fuel expenditure was **LKR 38.42 Billion** for March 2024.
   - Oil plants represented **27.69%** of generated energy but **58.3%** of total fuel expenditure, demonstrating the severe economic penalty of dispatching oil during hydro deficits.

3. **Transmission and Distribution Loss Trends (Q24)**:
   - Gross generation minus billed retail sales revealed a national loss proxy of **8.8% to 9.6%** over the 5-year historical window (2020–2024), consistent with audited CEB transmission and distribution losses.
