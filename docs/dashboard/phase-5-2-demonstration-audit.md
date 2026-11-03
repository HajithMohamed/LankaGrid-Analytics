# GridLens — Phase 5.2: Dashboard Accuracy, Interactive Filtering & Demonstration Readiness Audit

**Project:** GridLens — Sri Lanka National Electricity Grid Analytics Data Warehouse  
**Target:** Academic Demonstration & University Evaluation  
**Working Branch:** `fix/phase-5-dashboard-accuracy-and-demo`  
**Target Branch:** `development`  
**Author:** Senior Full-Stack Engineer, BI Analyst & Data Warehouse Architect  
**Date:** March 2026 / Academic Year 2026  

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 Unstyled UI Incident Investigation
During local preview testing, the application briefly rendered as unstyled HTML without stylesheet classes. A comprehensive technical autopsy revealed the root cause:
1. **Turbopack Caching & Module Resolution Glitch**: Next.js 16 defaults to Turbopack. When started initially on Windows under pnpm 11, Turbopack encountered an internal module resolution fault (`Can't resolve 'react/jsx-runtime'`) on dynamic client chunks.
2. **Missing Stylesheet Compilation**: Due to the compiler crash, the Next.js runtime served SSR HTML markup while failing to bundle or emit the CSS link targets (`/_next/static/css/...`). SVG elements (such as Recharts paths) rendered because they use inline SVG attributes, whereas CSS classes were absent.
3. **Stale Multi-Engine Artifacts**: Adding `--webpack` left orphaned `.next` artifacts that conflicted with hot reloads until a clean cache purge (`Remove-Item -Recurse -Force web/.next`) and fresh compilation were executed.
4. **Resolution Verified**: Verified clean build with `next build --webpack`. All 14 App Router routes compiled cleanly, producing a 27.4 KB optimized production CSS bundle (`a82ac0620d731b9c.css`) incorporating Tailwind CSS v4, custom theme tokens, and glassmorphic elevation styles.

---

## 2. Identified Discrepancies & Demonstration Risk Matrix

| Component / Area | Existing Behavior | Root Cause | University Demo Risk | Required Fix |
| :--- | :--- | :--- | :--- | :--- |
| **Executive Overview Year Filter** | Selecting year (e.g., 2022) does not dynamically recalculate annual billed sales KPI; sector table lacks dynamic sync. | Client code expected `calendar_year` / `economic_classification` rather than true SQL aliases `reporting_year` / `economic_sector_class`. | High (evaluators notice static KPI when interacting with filter dropdown). | Parse Q21 columns correctly; recalculate dynamic sales KPI from selected year; sync data table and highlight chart bar. |
| **Q21 GROUPING SETS Handling** | Sector percentages and sums risked double-counting rows where `grp_year = 1` or `grp_class = 1`. | SQL query utilizes `GROUPING SETS ((reporting_year, economic_sector_class), (reporting_year), ())`. | High (sector percentages could sum to >100% if subtotal rows are included). | Strictly filter rows by grouping indicator flags (`grp_year === 0 && grp_class === 0` for sectoral details; `grp_year === 0 && grp_class === 1` for annual totals). |
| **Q22 Reconciliation Variance** | UI reported single aggregated variance (3.971%) and attributed it to CEB sales digest. | Conflated CEB annual sales reconciliation ($\le 0.007\%$ max variance) with PUCSL daily operational dispatch (3.971% variance). | Critical (misrepresents CEB audited billing accuracy and confuses physical telemetry differences). | Separate reconciliation tiers into distinct KPI cards and table views: **CEB Audited Sales (0.007% max variance)** vs **PUCSL Daily Dispatch Telemetry (3.971% telemetry variance)**. |
| **Q23 Quarantined Subtotals** | Table showed 6 rows including rule subtotals and grand totals as if they were distinct rule violations. | `GROUPING SETS` in Q23 outputs detail rows, rule subtotal rows, and grand totals. | Moderate (double-counting 926 quarantined anomalies). | Parse `grp_rule` and `grp_class` flags to display exactly 2 detail rules (879 unmapped entities, 47 negative power) totaling 926. |
| **TopNav Connection Status** | Hardcoded `<TopNav isLive={true} />` regardless of actual PostgreSQL 18 connection status. | Static prop passed in server layout. | Moderate (does not dynamically indicate fallback to verified historical snapshots when database container is stopped). | Query `/api/metadata/coverage` dynamically in a client component or header banner to display real database connectivity. |
| **Warehouse Coverage Metadata** | Partitioned tables (e.g. `dw.fact_dispatch_interval` and its yearly child `fact_dispatch_interval_y2024`) risked duplicate row counting. | Partition inheritance in PostgreSQL information schema. | Moderate (row count inflation). | Deduplicate partition tables; label counts clearly as exact database count or verified snapshot count. |
| **Query Explorer Pedagogical Value** | Basic query viewer without explicit explanations of OLAP techniques or distinction between live execution vs snapshot loading. | Minimal metadata displayed. | High (misses opportunity to showcase academic mastery of `ROLLUP`, `CUBE`, `GROUPING SETS`, window functions, materialized views). | Add OLAP technique badges, SQL complexity tags, query intent breakdowns, and live vs snapshot toggles. |
| **Print & CSV Report Fidelity** | CSV export on Overview exported all historical years rather than filtering to the currently selected reporting year. | Export handler lacked active state parameter. | Moderate (inconsistent user experience during download). | Pass active `selectedYear` to CSV export generator; verify `@media print` styles hide navigation and controls cleanly. |

---

## 3. Implementation Plan & Work Breakdown

1. **Step 1: Executive Overview (`web/src/app/page.tsx` & `sales-trend-chart.tsx`)**
   - Implement dynamic year state (`2020` through `2024` or `ALL`).
   - Parse Q21 with grouping filters.
   - Dynamic Sales KPI: 2020 (14,287.00 GWh), 2021 (15,214.00 GWh), 2022 (14,520.00 GWh), 2023 (14,153.50 GWh), 2024 (15,190.50 GWh).
   - Dynamic Sector Breakdown table and CSV download.
   - Interactive chart click-to-filter with clear selection button.
   - Explicit "March 2024" period badges on generation mix KPIs.

2. **Step 2: Data Quality & Reconciliation (`web/src/app/data-quality/page.tsx`)**
   - Two-tier reconciliation display: CEB Audited Sales (0.007% max variance) vs PUCSL Daily Dispatch (3.971% operational variance).
   - Accurate Q23 quarantine breakdown: 879 entity unmapped + 47 negative active power = 926 total quarantined.
   - Accurate lineage documentation: lineage tracked via `audit.record_lineage` (surrogate mapping).

3. **Step 3: Database Connectivity & Metadata Coverage (`top-nav.tsx`, `coverage/route.ts`)**
   - Real-time or client-polled connectivity indicator in TopNav.
   - Partition-aware metadata counting with source classification.

4. **Step 4: Query Explorer Demonstration Enhancements (`web/src/app/query-explorer/page.tsx`)**
   - OLAP badges: `GROUPING SETS`, `ROLLUP`, `CUBE`, `LAG()`, `ROW_NUMBER()`, `MATERIALIZED VIEW`.
   - Clear visual indicator for "Live PostgreSQL 18 Query Execution" vs "Verified Historical Snapshot (Q01-Q24)".

5. **Step 5: Automated Testing & Verification**
   - Add automated test assertions in `tests/unit/test_dashboard_integrity.py` covering Q21 grouping filters, Q22 multi-tier variance separation, and Q23 subtotal handling.
   - Run linter (`ruff`), test suite (`pytest`), and Next.js production build (`pnpm run build`).

6. **Step 6: Demonstration Walkthrough Documentation**
   - Deliver `docs/dashboard/final-ui-demonstration-guide.md` with step-by-step presentation script for the team's project defense.

