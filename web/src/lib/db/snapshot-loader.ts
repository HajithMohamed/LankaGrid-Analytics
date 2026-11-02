import fs from "fs/promises";
import path from "path";
import { executeQuery } from "./client";
import { QUERY_REGISTRY, QueryDefinition } from "../analytics/query-registry";

export interface AnalyticsResult<T = Record<string, unknown>> {
  success: boolean;
  queryId: string;
  definition?: QueryDefinition;
  data: T[];
  rowCount: number;
  source: "live" | "snapshot";
  executionTimeMs?: number;
  sqlText?: string | null;
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
 * 1. Attempts live SQL execution against PostgreSQL 18
 * 2. On connection error or timeout, seamlessly falls back to authentic snapshot JSON
 */
export async function getAnalyticsData<T = Record<string, unknown>>(
  queryId: string
): Promise<AnalyticsResult<T>> {
  const def = QUERY_REGISTRY[queryId];
  const startTime = Date.now();
  const sqlText = await loadSqlFile(queryId);

  // Try live query if SQL text is available
  try {
    if (sqlText) {
      const res = await executeQuery<Record<string, unknown>>(sqlText);
      const executionTimeMs = Date.now() - startTime;
      return {
        success: true,
        queryId,
        definition: def,
        data: res.rows as T[],
        rowCount: res.rowCount ?? res.rows.length,
        source: "live",
        executionTimeMs,
        sqlText,
      };
    }
  } catch (liveError) {
    // If live query fails, fall back to snapshot
  }

  // Fallback to pre-computed authentic snapshot
  try {
    const snapshotData = await loadJsonSnapshot<T>(queryId);
    const executionTimeMs = Date.now() - startTime;
    return {
      success: true,
      queryId,
      definition: def,
      data: snapshotData,
      rowCount: snapshotData.length,
      source: "snapshot",
      executionTimeMs,
      sqlText,
    };
  } catch (snapshotError) {
    return {
      success: false,
      queryId,
      definition: def,
      data: [],
      rowCount: 0,
      source: "snapshot",
      sqlText,
      error: (snapshotError as Error).message,
    };
  }
}
