# GridLens Live Demonstration Pre-Flight Checklist
## National Electricity Grid Analytics Data Warehouse — Sri Lanka

**Document Reference:** `docs/demo/demo-checklist.md`  
**Purpose:** Pre-demonstration readiness verification, hardware/software checks, and fallback procedures.  

---

## 1. System Requirements & Prerequisites Checklist

| Component | Minimum Requirement | Verified Current State | Check Status |
| :--- | :--- | :--- | :---: |
| **Operating System** | Windows 10/11, macOS, or Ubuntu Linux | Windows 11 Enterprise | [x] READY |
| **Docker Engine** | Docker Desktop 4.20+ with Docker Compose v2 | Docker Engine 28.0.0 | [x] READY |
| **PostgreSQL Container** | PostgreSQL 18-alpine on port 5433 | `sl_grid_warehouse_db` (Healthy) | [x] READY |
| **Python Runtime** | Python 3.11 to 3.14 with virtual environment | Python 3.14.3 (`.venv`) | [x] READY |
| **Terminal / CLI** | PowerShell 7+, Bash, or Zsh | PowerShell on Windows | [x] READY |
| **Storage Space** | At least 2.0 GB free disk space | > 50 GB free | [x] READY |

---

## 2. Pre-Presentation Verification Protocol (T-Minus 15 Minutes)

Execute the following 5 verification commands in sequence before presenting:

```bash
# 1. Verify container is healthy and responding
docker exec -it sl_grid_warehouse_db pg_isready -U grid_admin -p 5432
# Expected: localhost:5432 - accepting connections

# 2. Verify schema migrations integrity (all 21 migrations applied)
.venv\Scripts\python.exe -c "
from src.common.config import DatabaseConfig
from src.common.db import get_connection
with get_connection(DatabaseConfig.from_env()) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM public.schema_migrations')
        print(f'Applied Migrations: {cur.fetchone()[0]}/21')
"
# Expected: Applied Migrations: 21/21

# 3. Verify warehouse row counts (facts and dimensions populated)
.venv\Scripts\python.exe -c "
from src.common.config import DatabaseConfig
from src.common.db import get_connection
with get_connection(DatabaseConfig.from_env()) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM dw.fact_dispatch_interval')
        print(f'Dispatch Interval Facts: {cur.fetchone()[0]:,}')
        cur.execute('SELECT COUNT(*) FROM dw.fact_weather_daily')
        print(f'Weather Facts: {cur.fetchone()[0]:,}')
        cur.execute('SELECT COUNT(*) FROM dw.fact_electricity_sales')
        print(f'Electricity Sales Facts: {cur.fetchone()[0]:,}')
"
# Expected:
# Dispatch Interval Facts: 107,115
# Weather Facts: 21,924
# Electricity Sales Facts: 44

# 4. Verify fast test suite execution
.venv\Scripts\pytest.exe tests/integration/test_migrations.py tests/analytics/test_phase3_olap.py -q
# Expected: 5 passed in < 5 seconds

# 5. Verify chart generation
.venv\Scripts\python.exe scripts/generate_phase3_charts.py
# Expected: All Phase 3 charts generated successfully in results/phase3/charts/.
```

---

## 3. Presentation Role Allocation & Query Assignments

| Presenter | Role & Domain | Assigned Queries | Key Technical Talking Points |
| :--- | :--- | :--- | :--- |
| **Member 1** | Generation Mix & Renewables | **Q01, Q02, Q03, Q04** | `ROLLUP` hierarchy, 7-day centered moving average, capacity factor vs peak utilization, TOU demand slicing. |
| **Member 2** | Grid Dispatch Dynamics | **Q05, Q06, Q07, Q08** | Diurnal load curves (weekday vs weekend), `LAG` 15-min ramp rate velocity, $CV$ baseload screening, Riemann telemetry reconciliation. |
| **Member 3** | Electricity Demand Dynamics | **Q09, Q10, Q11, Q12** | 5-year YoY trends, multi-year sector pivot, 16.46% CAGR hotel rebound, avoiding double-counting in LECO bulk supply. |
| **Member 4** | Weather & Renewable Coupling | **Q13, Q14, Q15, Q16** | Solar irradiance PSH profiles, `CORR` temperature-demand analysis, multi-dimensional `CUBE` rainfall, cubic wind correlation. |
| **Member 5** | Plant Operations & Capacity | **Q17, Q18, Q19, Q20** | Sentinel vs zero interval filtering, peak dispatch vs nameplate ratings, Lakvijaya baseload continuity, evening peak merit-order. |
| **Member 6** | Grid Efficiency & Quality | **Q21, Q22, Q23, Q24** | `GROUPING SETS` economic shift, multi-tier transmission loss proxy (8.8–9.6%), quarantine audit reconciliation (100%), pipeline throughput. |

---

## 4. Emergency Troubleshooting & Fallback Procedures

### Scenario A: Docker Container Stopped or Unresponsive
**Symptom:** `psycopg.OperationalError: connection to server at "localhost", port 5433 failed`.  
**Corrective Action:**
```bash
docker compose restart db
docker compose logs --tail=20 db
```

### Scenario B: Query Execution Delay During Presentation
**Symptom:** Terminal execution pauses unexpectedly during full fact scanning.  
**Explanation & Fallback:**  
Explain to evaluators: *"PostgreSQL is performing a cold-cache sequential scan over 107,115 rows. Notice the subsequent execution leverages cached shared buffers and partition pruning to execute in under 50 ms."*  
Alternatively, demonstrate the pre-computed materialized view:
```sql
SELECT * FROM mart.mv_daily_dispatch_by_source WHERE calendar_date = '2024-03-01';
-- Executes in 1.8 ms.
```

### Scenario C: Matplotlib Display Unavailable in Headless Terminal
**Symptom:** `UserWarning: Matplotlib is currently using agg, which is a non-GUI backend`.  
**Action:** Confirm that charts are saved directly as PNGs in `results/phase3/charts/` and open them via standard image viewer or web browser.

