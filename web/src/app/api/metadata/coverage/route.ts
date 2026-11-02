import { NextResponse } from "next/server";
import { executeQuery } from "@/lib/db/client";

export async function GET() {
  const startTime = Date.now();
  let dbStatus = "offline";
  let liveRowCounts: Record<string, number> = {};

  try {
    const res = await executeQuery<{
      table_name: string;
      approx_rows: string;
    }>(`
      SELECT relname AS table_name, n_live_tup AS approx_rows
      FROM pg_stat_user_tables
      WHERE schemaname = 'warehouse'
      ORDER BY relname;
    `);

    dbStatus = "connected";
    res.rows.forEach((row) => {
      liveRowCounts[row.table_name] = Number(row.approx_rows);
    });
  } catch (dbErr) {
    // DB offline, fall back to snapshot facts
    dbStatus = "snapshot_fallback";
  }

  const payload = {
    status: "ok",
    dbStatus,
    executionTimeMs: Date.now() - startTime,
    project: "GridLens — Sri Lanka National Electricity Grid Analytics Data Warehouse",
    institution: "University of Ruhuna, Faculty of Technology, Department of ICT",
    dataPeriod: "2020–2024",
    dimensions: [
      { name: "dim_date", type: "Calendar Date", rows: 1827 },
      { name: "dim_interval", type: "15-Minute TOU Interval", rows: 96 },
      { name: "dim_power_plant", type: "Generating Stations", rows: 54 },
      { name: "dim_energy_source", type: "Fuel Types & Renewables", rows: 9 },
      { name: "dim_consumption_sector", type: "Customer Sectors", rows: 10 },
      { name: "dim_weather_location", type: "Meteorological Stations", rows: 2 },
      { name: "dim_region", type: "CEB Administrative Regions", rows: 5 },
      { name: "dim_source_system", type: "Origin Systems", rows: 4 },
      { name: "dim_metric", type: "Published Indicators", rows: 8 },
    ],
    facts: [
      {
        name: "fact_dispatch_interval",
        grain: "15-minute generation per power plant",
        rows: liveRowCounts["fact_dispatch_interval_y2024"] || 107115,
        period: "March 2024 (PUCSL)",
      },
      {
        name: "fact_weather_daily",
        grain: "Daily meteorological observations",
        rows: liveRowCounts["fact_weather_daily"] || 21924,
        period: "2020–2024 (NASA POWER)",
      },
      {
        name: "fact_electricity_sales",
        grain: "Annual sector billing",
        rows: liveRowCounts["fact_electricity_sales"] || 49,
        period: "2020–2024 (CEB Audited)",
      },
      {
        name: "fact_generation_period",
        grain: "Annual utility generation summary",
        rows: liveRowCounts["fact_generation_period"] || 18,
        period: "2020–2024 (CEB Digest)",
      },
      {
        name: "quarantine_rejected_records",
        grain: "Data quality quarantine log",
        rows: 926,
        period: "Pipeline Cleanliness Audit",
      },
    ],
  };

  return NextResponse.json(payload, {
    headers: {
      "Cache-Control": "public, max-age=120, stale-while-revalidate=600",
    },
  });
}
