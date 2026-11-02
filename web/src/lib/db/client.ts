import { Pool, QueryResult, QueryResultRow } from "pg";

let pool: Pool | null = null;

export function getDbPool(): Pool {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL;
    pool = new Pool({
      connectionString,
      host: process.env.POSTGRES_HOST || "localhost",
      port: Number(process.env.POSTGRES_PORT || 5433),
      database: process.env.POSTGRES_DB || "sl_grid_warehouse",
      user: process.env.POSTGRES_USER || "grid_admin",
      password: process.env.POSTGRES_PASSWORD || "HAzi@1915",
      connectionTimeoutMillis: 2000,
      idleTimeoutMillis: 10000,
      max: 10,
    });

    pool.on("error", (err) => {
      console.warn("Unexpected error on idle PostgreSQL client pool:", err.message);
    });
  }
  return pool;
}

export async function executeQuery<T extends QueryResultRow = QueryResultRow>(
  sqlText: string,
  params: unknown[] = []
): Promise<QueryResult<T>> {
  const p = getDbPool();
  return p.query<T>(sqlText, params);
}
