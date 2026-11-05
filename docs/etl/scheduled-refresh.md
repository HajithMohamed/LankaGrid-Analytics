# Scheduled Data Refresh & Pipeline Operations

## 1. Operational Cadence

| Source | Cadence | Pipeline Driver | Target Fact Table |
| :--- | :--- | :--- | :--- |
| **PUCSL Dispatch Curves** | Daily / Monthly | `scripts/refresh_warehouse.py --dataset pucsl` | `dw.fact_dispatch_interval` |
| **NASA POWER Meteorological** | Daily / Weekly | `scripts/refresh_warehouse.py --dataset nasa` | `dw.fact_weather_daily` |
| **CEB Billed Sales** | Annual / Quarterly | `scripts/refresh_warehouse.py --dataset ceb` | `dw.fact_electricity_sales` |

---

## 2. GitHub Actions Automation

The automated refresh workflow is declared in `.github/workflows/scheduled-data-refresh.yml` and executes on a daily cron schedule at 02:00 UTC (07:30 Sri Lanka Standard Time).

### Workflow Steps:
1. Clones repository and sets up Python 3.12 environment.
2. Reads secure `DATABASE_URL` from GitHub repository secrets.
3. Invokes `python scripts/refresh_warehouse.py --verbose`.
4. Runs `python scripts/migrate_supabase.py --verify-only` to validate warehouse integrity.

---

## 3. Local Operational Commands

```powershell
# Refresh all available datasets
python scripts/refresh_warehouse.py

# Check status without database writes
python scripts/refresh_warehouse.py --dry-run

# Force re-ingestion of files
python scripts/refresh_warehouse.py --force
```

