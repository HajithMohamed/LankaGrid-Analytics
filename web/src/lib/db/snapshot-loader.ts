import fs from "fs/promises";
import path from "path";
import { executeQuery } from "./client";
import { QUERY_REGISTRY, QueryDefinition } from "../analytics/query-registry";

export interface AnalyticsResult<T = Record<string, unknown>> {
  success: boolean;
  queryId: string;
  source: "live" | "snapshot";
  sourceMode: "live" | "snapshot";
  data: T[];
  rowCount: number;
  period: string;
  attribution: string;
  executionTimeMs: number;
  definition?: QueryDefinition;
  sqlText?: string | null;
  dbErrorDiagnostic?: string | null;
  snapshotMeta?: {
    filename: string;
    sourceDataset: string;
  };
  error?: string;
}

/**
 * Locate a file across relative development paths
 */
async function findExistingFile(relativePaths: string[]): Promise<string | null> {
  for (const rel of relativePaths) {
    try {
      const fullPath = path.resolve(rel);
      await fs.access(fullPath);
      return fullPath;
    } catch {
      // Continue to next path
    }
  }
  return null;
}

/**
 * Load static JSON snapshot from disk
 */
export async function loadJsonSnapshot<T = Record<string, unknown>>(
  queryId: string
): Promise<T[]> {
  const possiblePaths = [
    path.join(process.cwd(), "public", "data", "snapshots", `${queryId}.json`),
    path.join(process.cwd(), "results", "phase3", "query-outputs", `${queryId}.json`),
    path.join(process.cwd(), "..", "results", "phase3", "query-outputs", `${queryId}.json`),
  ];

  const foundPath = await findExistingFile(possiblePaths);
  if (!foundPath) {
    throw new Error(`Snapshot JSON file for ${queryId} not found in searched paths.`);
  }

  const raw = await fs.readFile(foundPath, "utf-8");
  return JSON.parse(raw) as T[];
}

/**
 * Load static CSV file content from disk
 */
export async function loadCsvSnapshot(queryId: string): Promise<string> {
  const possiblePaths = [
    path.join(process.cwd(), "public", "data", "snapshots", `${queryId}.csv`),
    path.join(process.cwd(), "results", "phase3", "query-outputs", `${queryId}.csv`),
    path.join(process.cwd(), "..", "results", "phase3", "query-outputs", `${queryId}.csv`),
  ];

  const foundPath = await findExistingFile(possiblePaths);
  if (!foundPath) {
    throw new Error(`Snapshot CSV file for ${queryId} not found in searched paths.`);
  }

  return fs.readFile(foundPath, "utf-8");
}

/**
 * Load SQL query text from repository
 */
export async function loadSqlFile(queryId: string): Promise<string | null> {
  const def = QUERY_REGISTRY[queryId];
  if (!def) return null;

  const possiblePaths = [
    path.join(process.cwd(), def.sqlRelativePath),
    path.join(process.cwd(), "..", def.sqlRelativePath),
  ];

  const foundPath = await findExistingFile(possiblePaths);
  if (!foundPath) return null;

  return fs.readFile(foundPath, "utf-8");
}

/**
 * Unified Analytics Data Fetcher:
 * 1. Checks configured DATA_SOURCE_MODE ('live' | 'snapshot' | 'hybrid')
 * 2. Attempts live SQL execution against PostgreSQL 18
 * 3. On connection error or offline database in hybrid mode, gracefully falls back to authentic snapshot JSON
 */
export async function getAnalyticsData<T = Record<string, unknown>>(
  queryId: string
): Promise<AnalyticsResult<T>> {
  const def = QUERY_REGISTRY[queryId];
  const startTime = Date.now();
  const sqlText = await loadSqlFile(queryId);
  const mode = process.env.DATA_SOURCE_MODE || "hybrid";
  let dbDiagnostic: string | null = null;

  // 1. Live Query Execution (if allowed by mode)
  if (mode !== "snapshot" && sqlText) {
    try {
      const res = await executeQuery<Record<string, unknown>>(sqlText);
      const executionTimeMs = Date.now() - startTime;
      return {
        success: true,
        queryId,
        source: "live",
        sourceMode: "live",
        definition: def,
        data: res.rows as T[],
        rowCount: res.rowCount ?? res.rows.length,
        period: def?.period || "March 2024 / 2020–2024",
        attribution: `${def?.member || "Member"} (${def?.memberName || "Domain Specialist"})`,
        executionTimeMs,
        sqlText,
        dbErrorDiagnostic: null,
      };
    } catch (liveError) {
      dbDiagnostic = (liveError as Error).message;
      if (mode === "live") {
        // In strict live mode, do not mask failures
        return {
          success: false,
          queryId,
          source: "live",
          sourceMode: "live",
          definition: def,
          data: [],
          rowCount: 0,
          period: def?.period || "N/A",
          attribution: def?.member || "GridLens",
          executionTimeMs: Date.now() - startTime,
          sqlText,
          dbErrorDiagnostic: dbDiagnostic,
          error: `Live PostgreSQL query execution failed: ${dbDiagnostic}`,
        };
      }
    }
  }

  // 2. Fallback to pre-computed authentic snapshot
  try {
    const snapshotData = await loadJsonSnapshot<T>(queryId);
    const executionTimeMs = Date.now() - startTime;
    return {
      success: true,
      queryId,
      source: "snapshot",
      sourceMode: "snapshot",
      definition: def,
      data: snapshotData,
      rowCount: snapshotData.length,
      period: def?.period || "Historical (2020–2024)",
      attribution: `${def?.member || "Member"} (${def?.memberName || "Domain Specialist"}) [Verified Historical Snapshot]`,
      executionTimeMs,
      sqlText,
      dbErrorDiagnostic: dbDiagnostic,
      snapshotMeta: {
        filename: `${queryId}.json`,
        sourceDataset: def?.facts?.join(", ") || "Kimball Fact Constellation",
      },
    };
  } catch (snapshotError) {
    return {
      success: false,
      queryId,
      source: "snapshot",
      sourceMode: "snapshot",
      definition: def,
      data: [],
      rowCount: 0,
      period: def?.period || "Unknown",
      attribution: "GridLens Repository Snapshots",
      executionTimeMs: Date.now() - startTime,
      sqlText,
      dbErrorDiagnostic: dbDiagnostic,
      error: `Failed to load snapshot for ${queryId}: ${(snapshotError as Error).message}`,
    };
  }
}
