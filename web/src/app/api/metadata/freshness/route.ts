import { NextResponse } from "next/server";
import { executeQuery, getDbConfigSummary } from "@/lib/db/client";

export const dynamic = "force-dynamic";

export async function GET() {
  const startTime = Date.now();
  const dbSummary = getDbConfigSummary();

  try {
    // 1. Fetch latest ETL run
    const etlRes = await executeQuery<{
      pipeline_name: string;
      run_status: string;
      completed_at: string;
    }>(`
      SELECT pipeline_name, run_status, completed_at
      FROM audit.etl_run
      WHERE run_status IN ('SUCCEEDED', 'PARTIAL_QUARANTINE')
      ORDER BY completed_at DESC NULLS LAST
      LIMIT 1;
    `);
    const lastEtl = etlRes.rows[0] || null;

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

    // 4. Fetch fact & mart counts
    const countRes = await executeQuery<{ qualified_name: string; row_count: string }>(`
      SELECT 
        schemaname || '.' || relname AS qualified_name,
        COALESCE(n_live_tup, 0) AS row_count
      FROM pg_stat_user_tables
      WHERE schemaname IN ('dw', 'mart')
      ORDER BY schemaname, relname;
    `);

    const tableCounts: Record<string, number> = {};
    countRes.rows.forEach((r) => {
      tableCounts[r.qualified_name] = Number(r.row_count);
    });

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

    return NextResponse.json({
      status: "ok",
      connected: true,
      overallStatus,
      executionTimeMs: Date.now() - startTime,
      lastEtl: lastEtl
        ? {
            pipeline: lastEtl.pipeline_name,
            status: lastEtl.run_status,
            completedAt: lastEtl.completed_at,
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
        host: dbSummary.host,
        database: dbSummary.database,
        ssl: dbSummary.ssl,
      },
    });
  } catch (error) {
    return NextResponse.json({
      status: "error",
      connected: false,
      overallStatus: "OFFLINE",
      error: (error as Error).message,
      executionTimeMs: Date.now() - startTime,
      lastEtl: null,
      quarantinedRecords: 0,
      sources: [],
      tableCounts: {},
      connection: {
        host: dbSummary.host,
        database: dbSummary.database,
        ssl: dbSummary.ssl,
      },
    });
  }
}
