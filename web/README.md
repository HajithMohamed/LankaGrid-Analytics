# GridLens Analytics Dashboard — Next.js 16 BI Application

**Project:** GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka  
**Institution:** University of Ruhuna, Faculty of Technology, Department of ICT  
**Framework:** Next.js 16 App Router (React 19, TypeScript, Tailwind CSS v4, Lucide Icons, Recharts)  
**Database Engine:** PostgreSQL 18 (Dedicated least-privilege read-only role `grid_analyst`)  
**Design System:** Premium White Analytics (`#F8F9FB` canvas, `#FFFFFF` cards, `#19222D` typography)  

---

## 1. Overview & Architectural Role

The GridLens Dashboard provides an interactive, full-stack Business Intelligence interface for the Sri Lankan National Electricity Grid Analytics Data Warehouse. It enables domain researchers, academic evaluators, and grid planners to analyze 5 years of electricity generation, 15-minute dispatch dynamics, consumer tariff billing, and NASA POWER meteorological observations without altering the underlying database migrations or Python ETL pipelines.

### Key Architectural Tenets:
1. **Dual-Mode Data Architecture:**
   - **Primary (Live PostgreSQL 18):** Direct parameterized queries against `sl_grid_warehouse` via connection pooling using the `grid_analyst` role. Enforces a 5-second statement timeout and session read-only transaction defaults.
   - **Historical Snapshot Mode:** When the warehouse container is offline (e.g. during static auditing or offline presentation), the dashboard seamlessly serves pre-computed, authentic snapshots from `public/data/snapshots/` with a visible provenance badge.
2. **Controlled Semantic Layer:**
   - Enforces Kimball fact-grain compatibility (`web/src/lib/analytics/semantic-layer.ts`).
   - Prevents invalid cross-grain aggregations (e.g. cross-multiplying 15-minute interval dispatch with annual consumer billing).
   - Prohibits arbitrary SQL execution from the browser.
3. **Defense-in-Depth Security:**
   - Zero credentials committed to version control.
   - Database passwords read strictly from server environment variables.
   - Read-only database role (`grid_analyst`) enforced via migration `022_dashboard_readonly_role_and_security.sql`.
   - All 24 queries strictly allowlisted in `web/src/lib/analytics/query-registry.ts`.

---

## 2. Directory Structure

```text
web/
├── .env.example                     # Sanitized configuration template
├── package.json                     # Pinned dependencies (Next.js 16, React 19, Tailwind v4)
├── postcss.config.mjs               # PostCSS compiler config with @tailwindcss/postcss
├── tsconfig.json                    # Strict TypeScript configuration
├── public/
│   ├── data/snapshots/              # Authentic pre-computed Q01–Q24 JSON and CSV snapshots
│   └── gridlens-logo.svg            # Official vector mark
└── src/
    ├── app/
    │   ├── layout.tsx               # Root layout with TopNav and Footer
    │   ├── page.tsx                 # Executive Overview dashboard (KPIs, sales trends, mix)
    │   ├── overview/page.tsx        # Overview alias
    │   ├── generation/page.tsx      # Generation Mix & Renewables (Q01–Q04)
    │   ├── dispatch/page.tsx        # 15-Min Diurnal & Ramp Rate Dynamics (Q05–Q08)
    │   ├── sales/page.tsx           # 5-Year Sectoral Billing & Elasticity (Q09–Q12)
    │   ├── weather/page.tsx         # NASA POWER Solar & Temp Correlation (Q13–Q16)
    │   ├── plants/page.tsx          # Plant Outages & Capacity Envelopes (Q17–Q20)
    │   ├── data-quality/page.tsx    # Multi-Tier Reconciliations & Lineage (Q21–Q24)
    │   ├── query-explorer/page.tsx  # Predefined SQL & Semantic Layer Explorer
    │   └── api/
    │       ├── analytics/[queryId]/ # Allowlisted query execution route handler
    │       ├── analytics/semantic/  # Controlled semantic aggregation endpoint
    │       ├── exports/[queryId]/   # Live / filtered CSV export route handler
    │       └── metadata/coverage/   # Live PostgreSQL schema coverage & row counts
    ├── components/
    │   ├── charts/                  # Recharts wrappers (diurnal curves, donuts, bars)
    │   ├── dashboard/               # KpiCard, CoverageIndicator, badges
    │   ├── layout/                  # TopNav, PageHeader, Footer
    │   └── tables/                  # Governed DataTable with sorting and pagination
    └── lib/
        ├── analytics/
        │   ├── query-registry.ts    # Allowlist of Q01–Q24 definitions & metadata
        │   └── semantic-layer.ts    # Measures, dimensions, and fact-grain rules
        ├── db/
        │   ├── client.ts            # Read-only PostgreSQL 18 connection pool
        │   └── snapshot-loader.ts   # Dual-mode live query and snapshot fallback
        └── formatting/
            └── units.ts             # Strict electricity units (MW vs MWh/GWh)
```

---

## 3. Local Setup & Configuration

### Prerequisites:
- Node.js 20+
- `pnpm` 10+
- PostgreSQL 18 running in Docker (optional; snapshots are used if offline)

### Step 1: Clone & Configure Environment
```bash
cd web
copy .env.example .env.local
```

Edit `.env.local` to provide your local database password for the read-only role:
```ini
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=sl_grid_warehouse
POSTGRES_USER=grid_analyst
POSTGRES_PASSWORD=your_read_only_password_here
DATA_SOURCE_MODE=hybrid
```

### Step 2: Install Dependencies
```bash
pnpm install
```

### Step 3: Start Development Server
```bash
pnpm dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### Step 4: Build for Production
```bash
pnpm run build
pnpm start
```

---

## 4. Analytical Verification & Physical Units

| Unit | Physical Quantity | Usage in GridLens | Conversion |
|:--- |:--- |:--- |:--- |
| **MW** | Instantaneous Power (Demand / Capacity Rate) | 15-minute dispatch load curves, plant peak observed power, nameplate ratings. | $1\text{ MW} = 1{,}000\text{ kW}$ |
| **MWh** | Energy (Integrated work over time) | Monthly technology generation, station energy production. | $\text{MWh} = \text{MW} \times 0.25\text{ h}$ (15-min) |
| **GWh** | Large-scale Utility Energy | Annual statutory billed sales, national generation totals. | $1\text{ GWh} = 1{,}000\text{ MWh}$ |

**Physical Integrity Rules:**
- Never aggregate MW and MWh together.
- Never treat missing observations as zero ($0\text{ MW}$ signifies complete plant outage; missing data is represented as `NULL`).
- Q06 Maximum Ramp Rate: Verified as **141.00 MW** on March 17, 2024 at 18:30 (Interval 75, PEAK time block).
- Q22 Reconciliation: Multi-tier statutory digest reconciliation showing variance $\le 0.007\%$ for CEB sales and exact 48,223.00 MWh PUCSL March 1 control total.

---

## 5. Security & Credential Rotation Guidelines

If any database password was previously exposed in local development:
1. Immediately rotate the password on the PostgreSQL server:
   ```sql
   ALTER ROLE grid_analyst WITH PASSWORD 'new_strong_random_password';
   ```
2. Update `.env.local` with the new password.
3. Verify that `git status` does not track `.env.local` or `.env`.
4. Ensure `tests/unit/test_dashboard_integrity.py` passes to confirm zero exposed credentials.
