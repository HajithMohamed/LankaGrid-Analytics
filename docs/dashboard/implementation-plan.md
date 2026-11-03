# GridLens Next.js Analytics Dashboard — Implementation Plan

**Project:** GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka  
**Phase:** Phase 5 — Next.js Light-Mode Analytics Dashboard  
**Branch:** `feature/phase-5-nextjs-light-dashboard`  
**Target:** `development`  
**Framework:** Next.js 15+ (App Router), TypeScript, Tailwind CSS, shadcn/ui design tokens, Recharts, TanStack Table, Lucide React, `pg` (PostgreSQL client).

---

## 1. System Architecture & Objectives

The GridLens Analytics Dashboard provides an interactive web interface for the Sri Lankan National Electricity Grid Analytics Data Warehouse. It bridges the gap between the PostgreSQL 18 Kimball dimensional warehouse and end-user stakeholders (academic evaluators, grid analysts, policy planners) without altering the existing warehouse schema, migration runner, or Python ETL pipelines.

### Key Architectural Tenets:
1. **Light-Mode First UI/UX:** Built around modern, information-dense SaaS design tokens with a crisp white/light gray background (`#F7F9FC`), high-contrast dark slate typography (`#18324A`), muted blue/teal accents (`#12A88A`, `#3F7AE8`), and clean 12–16px card boundaries.
2. **Authentic Data Integrity:** 100% of KPIs, charts, and tables display real figures directly mapped to the 24 SQL analytical queries. No synthetic or fabricated metrics.
3. **Dual-Mode Data Architecture:**
   - **Primary (Live PostgreSQL 18):** Server-side data fetching via parameterized queries using `pg` pool connected to `sl_grid_warehouse` (port 5433).
   - **Snapshot Mode (Graceful Fallback):** When the database container is offline during CI/static auditing, the system serves pre-exported authentic JSON outputs from `results/phase3/query-outputs/`, with an explicit indicator badge.
4. **Zero-Client Secrets:** All database connections and query executions remain strictly server-side (Server Components and Route Handlers). No credentials exposed to the browser.
5. **Interactive Exploration & Export:** Dynamic filtering by date, time-of-use bucket, energy source, and sector, accompanied by live CSV exports for every analytical query.

---

## 2. Page & Metric to Query Mapping (24 Queries)

| Route / Page | Section / Card | Metric / Visualization | Source SQL Query & Fact Grain |
| :--- | :--- | :--- | :--- |
| **`/overview`** (Executive Overview) | KPI Grid | Total Generation (March 2024: 1,399,337.00 MWh)<br/>Renewable Share (29.75% avg)<br/>Coal Contribution (42.56%)<br/>2024 Billed Sales (15,190.50 GWh) | Q01 (`dw.fact_dispatch_interval`)<br/>Q02 (`dw.fact_dispatch_interval`)<br/>Q09 (`dw.fact_electricity_sales`) |
| | Dispatch Profile | 96-interval diurnal curve (weekday vs weekend) | Q05 (`dw.fact_dispatch_interval`) |
| | Generation Mix | Interactive Donut Chart by Energy Category | Q01 (`dw.fact_dispatch_interval`) |
| | 5-Year Sales Trend | Sectoral sales bars (2020–2024) | Q09 (`dw.fact_electricity_sales`) |
| | Data Coverage Info | 107,115 Dispatch facts, 21,924 Weather facts, 49 Sales facts, 926 Quarantined records | Warehouse Schema Catalog |
| **`/generation`** (Generation Analytics) | Generation Mix | Hierarchical ROLLUP breakdown table & donut | Q01 (`dw.fact_dispatch_interval`) |
| | Renewable Penetration | Daily trajectory with 7-day centered moving average | Q02 (`dw.fact_dispatch_interval`) |
| | Plant Capacity Factors | Official CF% vs observed peak utilization proxy | Q03 (`dw.fact_dispatch_interval` + `dim_power_plant`) |
| | TOU Regime Slicing | Daytime vs Evening Peak vs Off-Peak generation | Q04 (`dw.fact_dispatch_interval` + `dim_interval`) |
| **`/dispatch`** (Dispatch Analytics) | Diurnal Profiles | 96-slot 15-min curves (2,476 MW weekday peak) | Q05 (`dw.fact_dispatch_interval`) |
| | Ramp Rate Velocity | 15-min rate of change (+141 MW max surge at slot 75) | Q06 (`dw.fact_dispatch_interval`) |
| | Baseload vs Peaking | Coefficient of variation ($CV$) plant classification | Q07 (`dw.fact_dispatch_interval`) |
| | Energy Reconciliation | Discrete Riemann sum vs PUCSL Sheet 01.03 | Q08 (`dw.fact_dispatch_interval`) |
| **`/sales`** (Electricity Demand) | 5-Year Sector Trends | 2020–2024 annual sales by tariff sector | Q09 (`dw.fact_electricity_sales`) |
| | Sectoral Shifts | Tourism rebound (+83.94% CAGR +16.46%) vs Domestic | Q10 (`dw.fact_electricity_sales`) |
| | Account Intensity | Average monthly consumption (kWh/account/month) | Q11 (`dw.fact_electricity_sales`) |
| | LECO Bulk Partition | LECO bulk purchases (10.67%–11.23% share) | Q12 (`dw.fact_electricity_sales`) |
| **`/weather`** (Weather & Renewables) | Solar Resource Profiles | Peak Sun Hours (PSH/day) for Victoria & Mannar | Q13 (`dw.fact_weather_daily`) |
| | Temp vs Dispatch CORR | Pearson correlation ($r = +0.0083$ peak, $r = +0.1248$ daily) | Q14 (`dw.fact_weather_daily` + dispatch) |
| | Monsoon Rainfall CUBE | 5-Year rainfall cross-tabulation (Victoria: 63.54%) | Q15 (`dw.fact_weather_daily`) |
| | Wind Power Coupling | Correlation with 50m wind speed ($r = +0.7143$, $v^3$) | Q16 (`dw.fact_weather_daily` + dispatch) |
| **`/plants`** (Plant Operations) | Duty Cycle Audit | Zero-dispatch intervals (Lakvijaya 100%, Victoria 96.2%) | Q17 (`dw.fact_dispatch_interval`) |
| | Capacity Envelopes | Peak dispatch vs verified reference nameplate | Q18 (`dw.fact_dispatch_interval` + `dim_power_plant`) |
| | Baseload Continuity | Lakvijaya Coal units reliability (595,524.50 MWh) | Q19 (`dw.fact_dispatch_interval`) |
| | Evening Peak Merit | Hydro (32.40%) & Coal (39.67%) merit-order dispatch | Q20 (`dw.fact_dispatch_interval`) |
| **`/data-quality`** (Quality & ETL) | Economic Demand Share | Productive sector share expansion (50.35% to 55.64%) | Q21 (`dw.fact_electricity_sales`) |
| | Multi-Tier Reconciliation | CEB Sales vs Digest & PUCSL Daily Control Totals (variance <= 0.007%) | Q22 (`dw.fact_electricity_sales` + `dw.fact_dispatch_interval`) |
| | Quarantine Audit Trail | 926 quarantined records (879 entity, 47 negative) | Q23 (`audit.data_quality_issue`) |
| | Pipeline Lineage & SLA | 272,526 audit rows, loader throughput (rows/sec) | Q24 (`audit.record_lineage` + `etl_run`) |
| **`/query-explorer`** | Predefined Explorer | Allowlisted execution of all 24 queries with SQL, parameters, tabular data, execution plan, and CSV export | Queries Q01 through Q24 |

---

## 3. Directory Layout (`web/`)

```text
web/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.mjs
├── next.config.ts
├── public/
│   ├── favicon.ico
│   └── gridlens-logo.svg
└── src/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx (Redirects to /overview)
    │   ├── (dashboard)/
    │   │   ├── layout.tsx
    │   │   ├── overview/page.tsx
    │   │   ├── generation/page.tsx
    │   │   ├── dispatch/page.tsx
    │   │   ├── sales/page.tsx
    │   │   ├── weather/page.tsx
    │   │   ├── plants/page.tsx
    │   │   ├── data-quality/page.tsx
    │   │   └── query-explorer/page.tsx
    │   └── api/
    │       ├── analytics/
    │       │   ├── [queryId]/route.ts
    │       │   └── overview/route.ts
    │       ├── metadata/
    │       │   └── coverage/route.ts
    │       └── exports/
    │           └── [queryId]/route.ts
    ├── components/
    │   ├── layout/
    │   │   ├── sidebar.tsx
    │   │   ├── top-nav.tsx
    │   │   └── page-header.tsx
    │   ├── dashboard/
    │   │   ├── kpi-card.tsx
    │   │   ├── data-coverage-badge.tsx
    │   │   └── insight-banner.tsx
    │   ├── charts/
    │   │   ├── dispatch-curve-chart.tsx
    │   │   ├── generation-donut-chart.tsx
    │   │   ├── sales-trend-chart.tsx
    │   │   ├── renewable-trajectory-chart.tsx
    │   │   └── correlation-scatter-chart.tsx
    │   ├── tables/
    │   │   └── data-table.tsx
    │   └── ui/ (shadcn-compatible accessible primitives)
    ├── lib/
    │   ├── db/
    │   │   ├── client.ts (PostgreSQL connection pool & query executor)
    │   │   └── snapshot-loader.ts (Fallback loader from results/phase3/query-outputs)
    │   ├── analytics/
    │   │   ├── query-registry.ts (Metadata & definitions for Q01–Q24)
    │   │   └── query-runner.ts (Allowlisted query execution & formatting)
    │   ├── formatting/
    │   │   └── units.ts (MW, MWh, GWh, LKR, %, and ISO dates)
    │   └── constants/
    │       └── navigation.ts
    └── types/
        ├── analytics.ts
        └── queries.ts
```

---

## 4. Design System Tokens & Color Palette

- **Background:** `#F7F9FC` (Soft slate white)
- **Card Surface:** `#FFFFFF` with `border: 1px solid #E4EAF1`, `box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05)`
- **Primary Text:** `#18324A` (Deep navy slate)
- **Secondary Text:** `#6B788B` (Neutral steel gray)
- **Brand Primary Teal:** `#12A88A` (Clean renewable green-teal)
- **Accent Blue:** `#3F7AE8` (Hydro & transmission electric blue)
- **Accent Amber:** `#F2A73A` (Solar & warning accent)
- **Destructive/Outlier:** `#DC5964` (Quarantine & negative anomaly alert)
- **Border Radius:** `12px` (Cards), `8px` (Buttons, Inputs), `6px` (Badges)
- **Typography:** Inter / Geist Sans with crisp tabular numerals (`font-variant-numeric: tabular-nums`).

