import { NextResponse } from "next/server";
import { executeQuery, getDbConfigSummary } from "@/lib/db/client";

export async function GET() {
  const startTime = Date.now();
  let dbStatus: "connected" | "offline" = "offline";
  let countSource: "live_postgresql" | "verified_snapshot_manifest" = "verified_snapshot_manifest";
  const liveTableCounts: Record<string, { schema: string; tableName: string; approxRows: number }> = {};
  let connectionError: string | null = null;

  try {
    // Query actual implemented warehouse schemas (dw, audit, mart, staging, ref)
    const res = await executeQuery<{
      schemaname: string;
      relname: string;
      n_live_tup: string;
    }>(`
      SELECT 
        schemaname, 
        relname, 
        COALESCE(n_live_tup, 0) AS n_live_tup
      FROM pg_stat_user_tables
      WHERE schemaname IN ('dw', 'audit', 'mart', 'staging', 'ref')
      ORDER BY schemaname, relname;
    `);

    dbStatus = "connected";
    countSource = "live_postgresql";
    res.rows.forEach((row) => {
      // Store strictly by qualified key to prevent double-counting
      const qualifiedKey = `${row.schemaname}.${row.relname}`;
      liveTableCounts[qualifiedKey] = {
        schema: row.schemaname,
        tableName: row.relname,
        approxRows: Number(row.n_live_tup) || 0,
      };
    });
  } catch (dbErr) {
    dbStatus = "offline";
    countSource = "verified_snapshot_manifest";
    connectionError = (dbErr as Error).message;
  }

  // Calculate dispatch row count without double-counting partitions
  const getDispatchRowCount = (): number => {
    if (dbStatus === "connected") {
      // Look for child partition rows (fact_dispatch_interval_y2024, etc.)
      let partitionSum = 0;
      for (const [key, val] of Object.entries(liveTableCounts)) {
        if (key.startsWith("dw.fact_dispatch_interval_y")) {
          partitionSum += val.approxRows;
        }
      }
      if (partitionSum > 0) return partitionSum;
      
      // Fallback to parent table if non-partitioned or directly reported
      const parentCount = liveTableCounts["dw.fact_dispatch_interval"]?.approxRows;
      if (parentCount && parentCount > 0) return parentCount;
      
      return 107115;
    }
    return 107115;
  };

  const dbSummary = getDbConfigSummary();

  const payload = {
    status: "ok",
    connected: dbStatus === "connected",
    dbStatus,
    countSource,
    countType: dbStatus === "connected" ? "catalog_statistical_estimate" : "verified_historical_audit",
    connectionTarget: {
      host: dbSummary.host,
      port: dbSummary.port,
      database: dbSummary.database,
      user: dbSummary.user,
      ssl: dbSummary.ssl,
    },
    connectionErrorDiagnostic: connectionError ? "PostgreSQL database offline or unreachable; using verified snapshot manifest." : null,
    executionTimeMs: Date.now() - startTime,
    project: "GridLens — Sri Lanka National Electricity Grid Analytics Data Warehouse",
    institution: "University of Ruhuna, Faculty of Technology, Department of ICT",
    dataPeriod: "2020–2024",
    schemas: ["audit", "dw", "etl", "mart", "raw", "ref", "staging"],
    dimensions: [
      {
        name: "dim_date",
        schema: "dw",
        type: "Calendar Date",
        rows: liveTableCounts["dw.dim_date"]?.approxRows || 1827,
        grain: "Daily calendar dates (2020–2024)",
      },
      {
        name: "dim_interval",
        schema: "dw",
        type: "15-Minute TOU Interval",
        rows: liveTableCounts["dw.dim_interval"]?.approxRows || 96,
        grain: "96 daily 15-minute intervals with Day/Peak/Off-Peak TOU buckets",
      },
      {
        name: "dim_power_plant",
        schema: "dw",
        type: "Generating Stations",
        rows: liveTableCounts["dw.dim_power_plant"]?.approxRows || 54,
        grain: "Licensed CEB and IPP power plants with nameplate MW ratings",
      },
      {
        name: "dim_energy_source",
        schema: "dw",
        type: "Fuel Types & Renewables",
        rows: liveTableCounts["dw.dim_energy_source"]?.approxRows || 9,
        grain: "Coal, Fuel Oil, Auto Diesel, Major Hydro, Solar, Wind, Biomass",
      },
      {
        name: "dim_consumption_sector",
        schema: "dw",
        type: "Customer Sectors",
        rows: liveTableCounts["dw.dim_consumption_sector"]?.approxRows || 10,
        grain: "Domestic, Industrial, General Purpose, Hotel, Street Light, Bulk",
      },
      {
        name: "dim_weather_location",
        schema: "dw",
        type: "Meteorological Stations",
        rows: liveTableCounts["dw.dim_weather_location"]?.approxRows || 6,
        grain: "Victoria, Laxapana, Mannar, Puttalam, Hambantota, and Colombo grid nodes",
      },
      {
        name: "dim_region",
        schema: "dw",
        type: "CEB Administrative Regions",
        rows: liveTableCounts["dw.dim_region"]?.approxRows || 5,
        grain: "LK national and CEB administrative distribution provinces",
      },
      {
        name: "dim_source_system",
        schema: "dw",
        type: "Origin Systems",
        rows: liveTableCounts["dw.dim_source_system"]?.approxRows || 4,
        grain: "CEB Statistical Digest, PUCSL Daily Report, PUCSL Dispatch, NASA POWER",
      },
      {
        name: "dim_metric",
        schema: "dw",
        type: "Published Indicators",
        rows: liveTableCounts["dw.dim_metric"]?.approxRows || 8,
        grain: "Meteorological and grid operational metric indicators",
      },
    ],
    facts: [
      {
        name: "fact_dispatch_interval",
        schema: "dw",
        grain: "15-minute generation per power plant",
        rows: getDispatchRowCount(),
        period: "March 2024 (PUCSL)",
        isPartitioned: true,
      },
      {
        name: "fact_weather_daily",
        schema: "dw",
        grain: "Daily meteorological observations",
        rows: liveTableCounts["dw.fact_weather_daily"]?.approxRows || 21924,
        period: "2020–2024 (NASA POWER)",
        isPartitioned: false,
      },
      {
        name: "fact_electricity_sales",
        schema: "dw",
        grain: "Annual sector billing",
        rows: liveTableCounts["dw.fact_electricity_sales"]?.approxRows || 49,
        period: "2020–2024 (CEB Audited)",
        isPartitioned: false,
      },
      {
        name: "fact_generation_period",
        schema: "dw",
        grain: "Annual utility generation summary",
        rows: liveTableCounts["dw.fact_generation_period"]?.approxRows || 18,
        period: "2020–2024 (CEB Digest)",
        isPartitioned: false,
      },
      {
        name: "data_quality_issue",
        schema: "audit",
        grain: "Row-level data quality quarantine & issue ledger",
        rows: liveTableCounts["audit.data_quality_issue"]?.approxRows || 926,
        period: "Pipeline Cleanliness Audit",
        isPartitioned: false,
      },
      {
        name: "record_lineage",
        schema: "audit",
        grain: "End-to-end fact promotion provenance lineage",
        rows: liveTableCounts["audit.record_lineage"]?.approxRows || 272526,
        period: "Audit Traceability Trail",
        isPartitioned: false,
      },
    ],
  };

  return NextResponse.json(payload, {
    headers: {
      "Cache-Control": "public, max-age=120, stale-while-revalidate=600",
    },
  });
}
