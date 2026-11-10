import { NextRequest, NextResponse } from "next/server";
import { executeQuery, getDbConfigSummary } from "@/lib/db/client";

export const dynamic = "force-dynamic";

function isAuthorized(req: NextRequest): boolean {
  const configuredToken = process.env.MONITORING_API_TOKEN?.trim();
  if (!configuredToken) {
    return true;
  }
  const authHeader = req.headers.get("authorization") || "";
  const customHeader = req.headers.get("x-monitoring-token") || "";
  return (
    authHeader === `Bearer ${configuredToken}` ||
    customHeader === configuredToken
  );
}

export async function GET(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json(
      { status: "error", error: "Unauthorized monitoring endpoint request." },
      { status: 401 }
    );
  }

  const startTime = Date.now();
  const dbSummary = getDbConfigSummary();

  try {
    // 1. Fetch latest successful ETL run
    const etlRes = await executeQuery<{
      pipeline_name: string;
      run_status: string;
      completed_at: string;
      rows_inserted: string;
      rows_updated: string;
    }>(`
      SELECT
        pipeline_name,
        run_status,
        completed_at,
        COALESCE(rows_inserted, 0) AS rows_inserted,
        COALESCE(rows_updated, 0) AS rows_updated
      FROM audit.etl_run
      WHERE run_status IN ('SUCCEEDED', 'PARTIAL_QUARANTINE')
      ORDER BY completed_at DESC NULLS LAST
      LIMIT 1;
    `);
    const lastEtl = etlRes.rows[0] || null;

    // 1b. Fetch latest failed ETL error if any
    const errRes = await executeQuery<{
      pipeline_name: string;
      completed_at: string;
      error_message: string | null;
    }>(`
      SELECT pipeline_name, completed_at, error_message
      FROM audit.etl_run
      WHERE run_status IN ('FAILED', 'ROLLED_BACK')
        AND error_message IS NOT NULL
      ORDER BY completed_at DESC NULLS LAST
      LIMIT 1;
    `);
    const latestErrorRow = errRes.rows[0] || null;

    // 1c. Fetch latest materialized view refresh timestamp
    let lastMartRefreshAt: string | null = lastEtl?.completed_at || null;
    try {
      const martRes = await executeQuery<{ refreshed_at: string | null }>(`
        SELECT MAX(refreshed_at)::text AS refreshed_at
        FROM mart.mv_daily_dispatch_by_source;
      `);
      if (martRes.rows[0]?.refreshed_at) {
        lastMartRefreshAt = martRes.rows[0].refreshed_at;
      }
    } catch {
      // Fallback to lastEtl.completed_at
    }

    // 2. Fetch source documents summary per provider
    const sourcesRes = await executeQuery<{
      source_code: string;
      total_docs: string;
      last_acquired: string;
      latest_doc: string;
      latest_period: string;
    }>(`
      SELECT 
        s.source_code,
        COUNT(d.source_document_id) AS total_docs,
        MAX(d.created_at) AS last_acquired,
        (
          SELECT document_code 
          FROM raw.source_document d2 
          WHERE d2.source_system_id = s.source_system_id 
          ORDER BY d2.reporting_period_end DESC, d2.source_document_id DESC 
          LIMIT 1
        ) AS latest_doc,
        (
          SELECT reporting_period_end::text 
          FROM raw.source_document d2 
          WHERE d2.source_system_id = s.source_system_id 
          ORDER BY d2.reporting_period_end DESC, d2.source_document_id DESC 
          LIMIT 1
        ) AS latest_period
      FROM raw.source_system s
      LEFT JOIN raw.source_document d ON s.source_system_id = d.source_system_id
      GROUP BY s.source_system_id, s.source_code;
    `);

    // 3. Fetch quarantine count
    const quarRes = await executeQuery<{ total: string }>(`
      SELECT COUNT(*) AS total FROM audit.data_quality_issue;
    `);
    const quarantineCount = Number(quarRes.rows[0]?.total || 0);

    // 4. Fetch fact & mart counts (including materialized views via pg_class)
    const countRes = await executeQuery<{ qualified_name: string; row_count: string }>(`
      SELECT
        n.nspname || '.' || c.relname AS qualified_name,
        COALESCE(NULLIF(c.reltuples, -1)::bigint, 0) AS row_count
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname IN ('dw', 'mart')
        AND c.relkind IN ('r', 'm', 'p')
      ORDER BY n.nspname, c.relname;
    `);

    const tableCounts: Record<string, number> = {};
    countRes.rows.forEach((r) => {
      tableCounts[r.qualified_name] = Math.max(0, Number(r.row_count) || 0);
    });

    if (!tableCounts["dw.fact_dispatch_interval"]) {
      let partSum = 0;
      for (const [k, v] of Object.entries(tableCounts)) {
        if (k.startsWith("dw.fact_dispatch_interval_y")) {
          partSum += v;
        }
      }
      if (partSum > 0) {
        tableCounts["dw.fact_dispatch_interval"] = partSum;
      }
    }

    // Determine status
    let overallStatus = "HEALTHY";
    if (lastEtl && lastEtl.completed_at) {
      const diffMs = Date.now() - new Date(lastEtl.completed_at).getTime();
      const diffDays = diffMs / (1000 * 60 * 60 * 24);
      if (diffDays <= 2) {
        overallStatus = "FRESH";
      } else if (diffDays > 30) {
        overallStatus = "STALE";
      }
    }

    const queryExecutionTimeMs = Date.now() - startTime;

    return NextResponse.json({
      status: "ok",
      connected: true,
      dataSourceMode: "live_sql",
      overallStatus,
      executionTimeMs: queryExecutionTimeMs,
      queryExecutionTimeMs,
      lastEtlCompletedAt: lastEtl?.completed_at || null,
      lastMartRefreshAt,
      lastSourceError: latestErrorRow?.error_message || null,
      lastEtl: lastEtl
        ? {
            pipeline: lastEtl.pipeline_name,
            status: lastEtl.run_status,
            completedAt: lastEtl.completed_at,
            rowsInserted: Number(lastEtl.rows_inserted || 0),
            rowsUpdated: Number(lastEtl.rows_updated || 0),
          }
        : null,
      quarantinedRecords: quarantineCount,
      sources: sourcesRes.rows.map((s) => ({
        sourceCode: s.source_code,
        totalDocuments: Number(s.total_docs),
        lastAcquiredAt: s.last_acquired,
        latestDocumentCode: s.latest_doc,
        latestReportingPeriod: s.latest_period,
      })),
      tableCounts,
      connection: {
        database: dbSummary.database,
        ssl: dbSummary.ssl,
      },
    });
  } catch (error) {
    const queryExecutionTimeMs = Date.now() - startTime;
    return NextResponse.json({
      status: "error",
      connected: false,
      dataSourceMode: "offline_snapshot",
      overallStatus: "OFFLINE",
      error: "Database unreachable; serving verified snapshot state.",
      diagnostic: (error as Error).message,
      executionTimeMs: queryExecutionTimeMs,
      queryExecutionTimeMs,
      lastEtlCompletedAt: null,
      lastMartRefreshAt: null,
      lastSourceError: null,
      lastEtl: null,
      quarantinedRecords: 0,
      sources: [],
      tableCounts: {},
      connection: {
        database: dbSummary.database,
        ssl: dbSummary.ssl,
      },
    });
  }
}
