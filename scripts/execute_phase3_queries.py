"""
Phase 3 Analytical Query Execution, Export & Performance Benchmarking.
Executes all 24 queries (Q01-Q24), exports CSV/JSON results, and captures EXPLAIN plans.
"""

from __future__ import annotations

import csv
import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, LiteralString, cast

from src.common.config import DatabaseConfig
from src.common.db import get_connection


def default_serializer(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def run_phase3_pipeline() -> None:
    output_dir = Path("results/phase3/query-outputs")
    plans_dir = Path("results/phase3/execution-plans")
    output_dir.mkdir(parents=True, exist_ok=True)
    plans_dir.mkdir(parents=True, exist_ok=True)

    query_mapping = [
        # Member 1
        ("Q01", "database/queries/phase3/member_01_generation/Q01.sql", "Generation Mix by Energy Source"),
        ("Q02", "database/queries/phase3/member_01_generation/Q02.sql", "Renewable vs Non-Renewable Daily Share"),
        ("Q03", "database/queries/phase3/member_01_generation/Q03.sql", "Plant Capacity Factor Analysis"),
        ("Q04", "database/queries/phase3/member_01_generation/Q04.sql", "Peak Daytime Off-Peak Contribution"),
        # Member 2
        ("Q05", "database/queries/phase3/member_02_dispatch/Q05.sql", "Daily Dispatch Curves Weekday vs Weekend"),
        ("Q06", "database/queries/phase3/member_02_dispatch/Q06.sql", "Dispatch Ramp Rate Analysis"),
        ("Q07", "database/queries/phase3/member_02_dispatch/Q07.sql", "Baseload vs Peaking Plant Behavior"),
        ("Q08", "database/queries/phase3/member_02_dispatch/Q08.sql", "Telemetry to Published Energy Reconciliation"),
        # Member 3
        ("Q09", "database/queries/phase3/member_03_sales/Q09.sql", "Five-Year Sectoral Electricity Sales Trends"),
        ("Q10", "database/queries/phase3/member_03_sales/Q10.sql", "Sectoral Consumption Shifts Across Historical Periods"),
        ("Q11", "database/queries/phase3/member_03_sales/Q11.sql", "Average Consumption per Customer Account"),
        ("Q12", "database/queries/phase3/member_03_sales/Q12.sql", "LECO Bulk Supply vs Direct CEB Sales"),
        # Member 4
        ("Q13", "database/queries/phase3/member_04_weather/Q13.sql", "Five-Year Solar Irradiance Profiles"),
        ("Q14", "database/queries/phase3/member_04_weather/Q14.sql", "Temperature and Grid Demand Correlation"),
        ("Q15", "database/queries/phase3/member_04_weather/Q15.sql", "Rainfall and Solar Monsoon Seasonality"),
        ("Q16", "database/queries/phase3/member_04_weather/Q16.sql", "Wind Resource Distribution and Generation Relationship"),
        # Member 5
        ("Q17", "database/queries/phase3/member_05_plant_operations/Q17.sql", "Zero-Generation Interval Analysis"),
        ("Q18", "database/queries/phase3/member_05_plant_operations/Q18.sql", "Installed Capacity Utilization Ratio"),
        ("Q19", "database/queries/phase3/member_05_plant_operations/Q19.sql", "Lakvijaya Coal Unit Dispatch Continuity"),
        ("Q20", "database/queries/phase3/member_05_plant_operations/Q20.sql", "Evening Peak Generation Contribution"),
        # Member 6
        ("Q21", "database/queries/phase3/member_06_grid_efficiency/Q21.sql", "Five-Year Grid Sales Efficiency Trends"),
        ("Q22", "database/queries/phase3/member_06_grid_efficiency/Q22.sql", "Cross-Source Multi-Tier Reconciliation"),
        ("Q23", "database/queries/phase3/member_06_grid_efficiency/Q23.sql", "Data Quality Quarantine Audit Trail"),
        ("Q24", "database/queries/phase3/member_06_grid_efficiency/Q24.sql", "ETL Execution Performance and Lineage"),
    ]

    cfg = DatabaseConfig.from_env(use_test_db=False)
    summary_records = []

    with get_connection(cfg) as conn:
        for q_id, q_path, q_desc in query_mapping:
            sql_text = cast(LiteralString, Path(q_path).read_text(encoding="utf-8"))
            with conn.cursor() as cur:
                t0 = time.perf_counter()
                cur.execute(sql_text)
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

                assert cur.description is not None, f"Cursor description is None for {q_id}"
                col_names = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                # Export CSV
                csv_path = output_dir / f"{q_id}.csv"
                with open(csv_path, "w", newline="", encoding="utf-8") as f_csv:
                    writer = csv.writer(f_csv)
                    writer.writerow(col_names)
                    writer.writerows(rows)

                # Export JSON
                dict_rows = [dict(zip(col_names, r, strict=True)) for r in rows]
                json_path = output_dir / f"{q_id}.json"
                with open(json_path, "w", encoding="utf-8") as f_json:
                    json.dump(dict_rows, f_json, default=default_serializer, indent=2)

                print(f"[{q_id}] {q_desc}: {len(rows)} rows, {elapsed_ms} ms -> {csv_path.name}")
                summary_records.append({
                    "query_id": q_id,
                    "title": q_desc,
                    "row_count": len(rows),
                    "execution_time_ms": elapsed_ms,
                })

                # Capture EXPLAIN (ANALYZE, BUFFERS) for representative queries
                if q_id in ("Q01", "Q05", "Q09", "Q15", "Q17", "Q24"):
                    explain_sql = cast(LiteralString, f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql_text}")
                    cur.execute(explain_sql)
                    row_plan = cur.fetchone()
                    assert row_plan is not None, f"Explain plan row is None for {q_id}"
                    explain_plan = row_plan[0]
                    plan_path = plans_dir / f"{q_id}_explain_analyze.json"
                    with open(plan_path, "w", encoding="utf-8") as f_plan:
                        json.dump(explain_plan, f_plan, indent=2)

    # Export execution summary
    summary_path = output_dir / "execution_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f_sum:
        json.dump(summary_records, f_sum, indent=2)
    print(f"\nPhase 3 execution completed. Summary saved to {summary_path}")


if __name__ == "__main__":
    run_phase3_pipeline()

