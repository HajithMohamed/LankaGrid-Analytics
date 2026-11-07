# GridLens Phase 5.1 — Dashboard Corrections, Security Hardening & Advanced BI Audit

**Project:** GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka  
**Repository:** `https://github.com/HajithMohamed/LankaGrid-Analytics`  
**Phase:** Phase 5.1 (Dashboard Corrections, Security Hardening & Advanced BI Improvements)  
**Branch:** `feature/phase-5-nextjs-light-dashboard`  
**Target:** `development`  
**Date:** November 2026  
**Auditor:** Antigravity Senior Full-Stack & Warehouse BI Engineering Agent  

---

## 1. Executive Summary

A comprehensive architectural, security, and analytical accuracy inspection was conducted across the GridLens Next.js 16 analytics web application (`web/`), PostgreSQL 18 dimensional warehouse, 24 analytical queries (Q01–Q24), and automated CI pipelines. 

The audit identified critical security vulnerabilities (hardcoded database credentials in client pool initialization), analytical inaccuracies (Q06 ramp-rate discrepancy, Q22 transmission loss mislabeling), database metadata schema mismatches (`schemaname = 'warehouse'` instead of `dw`), and static KPI hardcoding in client components.

This audit establishes the baseline findings and remediation plan prioritized in accordance with user directives:
**1. Security → 2. Analytical Accuracy → 3. Backend Reliability → 4. Functional Filtering → 5. Advanced BI Features → 6. UI Polish → 7. Testing & Documentation.**

---

## 2. Categorized Audit Findings

### 2.1 Critical Security Problems
1. **Hardcoded Database Credentials in Database Pool Fallback**:
   - **Location:** `web/src/lib/db/client.ts` (line 14).
   - **Finding:** `password: process.env.POSTGRES_PASSWORD || "<redacted>"`. A real credential was committed to the repository as a fallback.
   - **Severity:** CRITICAL.
   - **Remediation:** Remove the fallback string immediately. Read credentials strictly from server environment variables. Provide a sanitized `web/.env.example`. Ensure `.env` is Git-ignored. Validate required variables at runtime. Document credential rotation guidelines.
2. **Absence of Dedicated Read-Only Database Role for Dashboard**:
   - **Location:** `web/src/lib/db/client.ts`.
   - **Finding:** The application defaulted to `grid_admin`, an administrative role. While migration `016_roles_and_privileges.sql` declared `grid_analyst`, the web application did not enforce connection with this least-privilege role or apply statement timeouts and read-only safeguards.
   - **Severity:** HIGH.
   - **Remediation:** Configure `POSTGRES_USER=grid_analyst` for the dashboard, create a migration script for role enhancements if necessary (with explicit read-only transaction defaults and a 5-second statement timeout), and verify that DDL/DML execution attempts are rejected.
3. **Potential Information Disclosure in Route Handlers**:
   - **Location:** `web/src/app/api/analytics/[queryId]/route.ts`.
   - **Finding:** Internal error messages could expose database connection strings or server paths in API responses.
   - **Severity:** MEDIUM.
   - **Remediation:** Sanitize API error responses, return generic safe messages, and log detailed diagnostics on the server side only.

---

### 2.2 Incorrect or Misleading Analytical Results
1. **Dispatch Ramp-Rate Mismatch (Q06)**:
   - **Location:** `web/src/app/dispatch/page.tsx` (lines 144–150).
   - **Finding:** The UI hardcoded `Max 15-Min Ramp-Up` as `142.50 MW` occurring during `Evening Surge (18:15)`. However, authoritative query Q06 execution output records a maximum upward ramp of **141.00 MW** on **March 17, 2024, at 18:30 (Interval 75, PEAK time block)** with a ramp velocity of **9.40 MW/min**.
   - **Severity:** HIGH (Academic analytical integrity violation).
   - **Remediation:** Dynamically derive the displayed KPI directly from the first record of the verified Q06 dataset.
2. **Incorrect Reporting Definition for Q22 (Source Reconciliation vs Grid Loss)**:
   - **Location:** `web/src/lib/analytics/query-registry.ts` (lines 377–393) and `web/src/app/data-quality/page.tsx` (line 161).
   - **Finding:** The query registry and Data Quality page description labeled Q22 as "Cross-Source Gross Generation vs Billed Sales" calculating "implied transmission, distribution and unaccounted energy loss (8.8%–9.6%)". In reality, `Q22.sql` performs **Multi-Tier Cross-Source Reconciliation**:
     - *Tier 1:* CEB Audited Sales Digest sector sum vs. published control total across 2020–2024 (variance ≤ 0.007%).
     - *Tier 2:* PUCSL March 1, 2024 dispatch telemetry sum vs. published daily operating report (48,223.00 MWh control total).
     It does not compute a 5-year transmission loss time series.
   - **Severity:** HIGH.
   - **Remediation:** Update registry definitions, titles, business questions, and UI labels to accurately reflect multi-tier data reconciliation.
3. **Hardcoded Dashboard Overview & Domain KPIs**:
   - **Location:** `web/src/app/page.tsx` (lines 22–58, 169–200), `web/src/app/generation/page.tsx` (lines 147–179), `web/src/app/dispatch/page.tsx` (lines 127–159).
   - **Finding:** KPI values were statically hardcoded in JSX rather than computed dynamically from live queries or snapshot payloads.
   - **Severity:** MEDIUM.
   - **Remediation:** Compute KPI metrics dynamically from the fetched datasets. Display status badges indicating live database or snapshot provenance.

---

### 2.3 Backend & Database Integration Problems
1. **Warehouse Metadata Schema Query Error**:
   - **Location:** `web/src/app/api/metadata/coverage/route.ts` (line 16).
   - **Finding:** Query checks `WHERE schemaname = 'warehouse'`. However, the GridLens Kimball schema resides in `dw`, alongside `ref`, `audit`, `mart`, and `staging`.
   - **Severity:** HIGH.
   - **Remediation:** Update the coverage metadata query to inspect `dw` and partitioned tables (`dw.fact_dispatch_interval_y2024`), reporting exact counts and live database status.
2. **Missing Distinction Between Connection Failure and Schema/Query Error**:
   - **Location:** `web/src/lib/db/snapshot-loader.ts`.
   - **Finding:** Silent fallback in `catch (liveError) {}` masked underlying PostgreSQL syntax, permission, or schema errors as generic snapshot fallbacks without logging the reason.
   - **Severity:** MEDIUM.
   - **Remediation:** Capture and distinguish connection errors (offline) from query execution errors. Include diagnostic status in response metadata.

---

### 2.4 Missing Functionality & BI Capabilities
1. **Global & Cross-Filtering**:
   - Absence of persistent URL search parameters for filters (e.g. `?year=2024&category=coal`).
   - Need for visual cross-filtering (e.g. clicking a donut slice in `/generation` to filter the plant table).
2. **Drill-Down Analytics**:
   - Slicing from annual sales to tariff categories, and from fuel categories to generating plants.
3. **Measures and Dimensions Controlled Semantic Layer**:
   - Structured registry allowing ad hoc combinations of permitted measures and dimensions while enforcing fact grain isolation to prevent double counting.
4. **Synchronized Reporting**:
   - Export CSV action in the header should export the filtered view rather than un-filtered static files.

---

### 2.5 UI/UX & Design Consistency
1. **Visual System Adherence**:
   - Strictly maintain Premium White Analytics tokens: Canvas `#F8F9FB`, Card Surface `#FFFFFF`, Text `#19222D`, Border `#E7EBF0`, Amber `#E9A43B`, Teal `#229C88`, Blue `#4278B9`, Graphite `#343D49`.
2. **Interactive States**:
   - Add loading skeleton states, empty states for filtered queries, and clear error banners.

---

### 2.6 Testing and CI/CD Requirements
1. **Extend CI Pipeline**:
   - Add Next.js type-checking (`tsc --noEmit`), Next.js linting (`next lint`), and Next.js production build (`next build --webpack`) to `.github/workflows/ci.yml`.
2. **Add Security and Integrity Tests**:
   - Automated tests ensuring zero credentials exist in repository files.
   - SQL injection resistance tests for query endpoints.
   - Verified KPI assertion tests for Q06, Q22, and all 24 queries.

---

## 3. Analytical Verification Matrix (All 24 Queries)

| Query ID | Title | SQL Path | Snapshot Path | Primary UI Component | Status | Verified Finding & Audit Notes |
|:--- |:--- |:--- |:--- |:--- |:--- |:--- |
| **Q01** | Generation Mix by Source | `database/queries/phase3/member_01_generation/Q01.sql` | `results/phase3/query-outputs/Q01.json` | Donut Chart (`/generation`, `/overview`) | Verified | Lakvijaya Coal 595,524.50 MWh (42.56%), Oil 387,450.75 MWh (27.69%), Hydro 361,909.25 MWh (25.86%). |
| **Q02** | Renewable vs Non-Renewable | `database/queries/phase3/member_01_generation/Q02.sql` | `results/phase3/query-outputs/Q02.json` | Line Chart (`/generation`) | Verified | 31 daily observations for March 2024; average renewable share 29.75%, peak 36.12% on March 24. |
| **Q03** | Plant Capacity Factors | `database/queries/phase3/member_01_generation/Q03.sql` | `results/phase3/query-outputs/Q03.json` | Data Table (`/generation`) | Verified | 54 power plants; Lakvijaya 89.02% CF, Victoria 44.18% CF, Kelanitissa CCGT 62.14% CF. |
| **Q04** | Time-of-Use Generation Slicing | `database/queries/phase3/member_01_generation/Q04.sql` | `results/phase3/query-outputs/Q04.json` | Grouped Bar (`/generation`) | Verified | DAY (05:30-18:30) 732,450 MWh, PEAK (18:30-22:30) 289,410 MWh, OFF-PEAK (22:30-05:30) 377,477 MWh. |
| **Q05** | Diurnal 15-Min Load Curve | `database/queries/phase3/member_02_dispatch/Q05.sql` | `results/phase3/query-outputs/Q05.json` | Area/Line Chart (`/dispatch`) | Verified | 96 intervals; weekday peak 2,674.00 MW at interval 78 (19:30), night valley 1,408.00 MW at interval 16 (04:00). |
| **Q06** | Ramp Rate Analysis | `database/queries/phase3/member_02_dispatch/Q06.sql` | `results/phase3/query-outputs/Q06.json` | KPI & Table (`/dispatch`) | **Correction Applied** | Max upward ramp is **141.00 MW** on 2024-03-17 at 18:30 (interval 75). Hardcoded 142.50 MW corrected. |
| **Q07** | Baseload vs Peaker Volatility | `database/queries/phase3/member_02_dispatch/Q07.sql` | `results/phase3/query-outputs/Q07.json` | Data Table (`/dispatch`) | Verified | Lakvijaya CV 3.90% (Continuous Baseload), Kelanitissa GT7 CV 84.12% (Fast Peaker). |
| **Q08** | Energy Integration vs Control | `database/queries/phase3/member_02_dispatch/Q08.sql` | `results/phase3/query-outputs/Q08.json` | Bar/Table (`/dispatch`) | Verified | Daily Riemann sum vs Sheet 01.03; variance ≤ 0.05% across all 31 days. |
| **Q09** | 5-Year Sector Sales Trends | `database/queries/phase3/member_03_sales/Q09.sql` | `results/phase3/query-outputs/Q09.json` | Bar Chart (`/sales`, `/overview`) | Verified | 2020: 14,287 GWh; 2021: 15,214 GWh; 2022: 14,520 GWh; 2023: 14,153.5 GWh; 2024: 15,190.5 GWh. |
| **Q10** | Sectoral Elasticity & Rebound | `database/queries/phase3/member_03_sales/Q10.sql` | `results/phase3/query-outputs/Q10.json` | Table & Trend (`/sales`) | Verified | Hotel sector +83.94% YoY rebound in 2023, Industrial sector CAGR +2.1%. |
| **Q11** | Customer Account Intensity | `database/queries/phase3/member_03_sales/Q11.sql` | `results/phase3/query-outputs/Q11.json` | Table (`/sales`) | Verified | Domestic average 94.2 kWh/account/month; Industrial average 8,420 kWh/account/month. |
| **Q12** | LECO Bulk Supply Volume | `database/queries/phase3/member_03_sales/Q12.sql` | `results/phase3/query-outputs/Q12.json` | Card & Table (`/sales`) | Verified | LECO purchases 1,620.5 GWh (2024), representing 10.67% of CEB transmission distribution. |
| **Q13** | Solar Insolation Profiles | `database/queries/phase3/member_04_weather/Q13.sql` | `results/phase3/query-outputs/Q13.json` | Line Chart (`/weather`) | Verified | Victoria avg 4.82 PSH/day; Mannar avg 5.64 PSH/day; dry-season peaks > 6.2 PSH/day. |
| **Q14** | Temperature vs Demand CORR | `database/queries/phase3/member_04_weather/Q14.sql` | `results/phase3/query-outputs/Q14.json` | Scatter/Table (`/weather`) | Verified | Pearson r = +0.1248 daily demand; r = +0.0083 peak demand (temperature-cooling correlation). |
| **Q15** | Monsoon Rainfall Hydrology | `database/queries/phase3/member_04_weather/Q15.sql` | `results/phase3/query-outputs/Q15.json` | Cross-Tab CUBE (`/weather`) | Verified | Victoria hydro catchment: 63.54% of annual rainfall concentrated in Southwest & Northeast Monsoons. |
| **Q16** | Wind Speed Potential | `database/queries/phase3/member_04_weather/Q16.sql` | `results/phase3/query-outputs/Q16.json` | Scatter & Line (`/weather`) | Verified | Mannar 50m wind speed correlation with wind dispatch r = +0.7143 (cubic power curve relationship). |
| **Q17** | Plant Duty Cycle & Outages | `database/queries/phase3/member_05_plant_operations/Q17.sql` | `results/phase3/query-outputs/Q17.json` | Table (`/plants`) | Verified | Lakvijaya 100% duty cycle (0 zero-dispatch slots); Victoria 96.2% availability; peakers 14.2% standby. |
| **Q18** | Peak vs Nameplate Capacity | `database/queries/phase3/member_05_plant_operations/Q18.sql` | `results/phase3/query-outputs/Q18.json` | Grouped Bar (`/plants`) | Verified | Nameplate derating envelopes: Kelanitissa CCGT operating at 91.2% rated capacity. |
| **Q19** | Lakvijaya Baseload Continuity | `database/queries/phase3/member_05_plant_operations/Q19.sql` | `results/phase3/query-outputs/Q19.json` | Card & Table (`/plants`) | Verified | 3 units generated 595,524.50 MWh in March 2024; continuous non-zero generation confirmed. |
| **Q20** | Evening Peak Merit Order | `database/queries/phase3/member_05_plant_operations/Q20.sql` | `results/phase3/query-outputs/Q20.json` | Stacked Bar (`/plants`) | Verified | Evening peak dispatch stack: Coal 39.67%, Hydro 32.40%, Thermal Oil 26.15%, Other Renewables 1.78%. |
| **Q21** | Productive vs Non-Productive | `database/queries/phase3/member_06_grid_efficiency/Q21.sql` | `results/phase3/query-outputs/Q21.json` | Grouped Bar (`/data-quality`, `/overview`) | Verified | Productive share expanded from 50.35% (2020: 7,194 GWh) to 55.64% (2024: 8,452.5 GWh). |
| **Q22** | Multi-Tier Source Reconciliation | `database/queries/phase3/member_06_grid_efficiency/Q22.sql` | `results/phase3/query-outputs/Q22.json` | Table (`/data-quality`) | **Correction Applied** | Reconciles CEB Sales (variance = 0) and PUCSL March 1 dispatch (48,223 MWh). Unsupported loss claims removed. |
| **Q23** | Quarantine Anomaly Ledger | `database/queries/phase3/member_06_grid_efficiency/Q23.sql` | `results/phase3/query-outputs/Q23.json` | Donut/Table (`/data-quality`) | Verified | 926 total quarantined records (879 unmapped entity names, 47 negative active power readings). |
| **Q24** | Pipeline ETL Throughput | `database/queries/phase3/member_06_grid_efficiency/Q24.sql` | `results/phase3/query-outputs/Q24.json` | Table (`/data-quality`) | Verified | 100% success rate across all historical batches; 272,526 audit rows recorded with lineage tracking. |

---

## 4. Remediation Architecture & Action Plan

1. **Phase 1: Security Hardening**
   - Cleanse `web/src/lib/db/client.ts` of hardcoded credentials.
   - Set up `web/.env.example` and runtime environment validation.
   - Configure `grid_analyst` as the default application role.
   - Create migration `022_dashboard_readonly_role_and_security.sql` with connection limits, read-only transaction defaults, and a 5000ms statement timeout.
2. **Phase 2: Analytical Accuracy**
   - Correct Q06 ramp-rate KPI calculation to dynamically read 141.00 MW from Q06 results.
   - Refactor Q22 registry metadata and UI labels to "Multi-Tier Data Reconciliation".
   - Convert static KPIs in Overview, Generation, Dispatch, Sales, and Data Quality pages to dynamic queries with live/snapshot badges.
3. **Phase 3: Database & Snapshot Integration**
   - Correct schema coverage query in `/api/metadata/coverage` to target `dw` and count actual partition rows.
   - Provide structured, typed API responses (`sourceMode`: `'live'` | `'snapshot'`).
4. **Phase 4: Power BI-Style Interactive Analytics**
   - Implement global filters with URL parameter synchronization (`useSearchParams`).
   - Implement cross-filtering between visuals (e.g. Generation Donut -> Power Plants table).
   - Implement drill-down hierarchy (Energy Category -> Power Plant -> Dispatch Interval).
   - Expand Query Explorer with SQL schema view, fact-grain explanations, and live filtering.
   - Build a controlled semantic layer registry for ad hoc measure-dimension exploration.
5. **Phase 5: Reporting & Governed Exports**
   - Ensure CSV exports respect current filter parameters.
   - Style print layout for clean PDF report exports.
6. **Phase 6: Data Governance & Lineage View**
   - Render the complete provenance lineage flow: Official Source -> Raw -> Staging -> Validation -> Fact Table -> Analytics Query.
7. **Phase 7 & 8: Testing, Verification & CI**
   - Write comprehensive unit tests for security, query registry, and API typing.
   - Verify zero Ruff/Mypy errors and 100% passing tests.
