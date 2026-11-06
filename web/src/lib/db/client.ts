import { Pool, QueryResult, QueryResultRow } from "pg";

let pool: Pool | null = null;

export interface DbConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  hasPassword: boolean;
  ssl: boolean;
}

/**
 * Return non-sensitive database connection metadata for health/coverage reporting.
 * Never exposes passwords or secret connection strings.
 */
export function getDbConfigSummary(): DbConfig {
  const dbUrl = process.env.DATABASE_URL;
  if (dbUrl) {
    try {
      const parsed = new URL(dbUrl);
      const isSupabase =
        parsed.hostname.includes("supabase.co") || parsed.hostname.includes("supabase.com");
      return {
        host: parsed.hostname,
        port: parsed.port ? Number(parsed.port) : 5432,
        database: parsed.pathname ? parsed.pathname.replace(/^\//, "") : "postgres",
        user: parsed.username || "postgres",
        hasPassword: Boolean(parsed.password),
        ssl: isSupabase || process.env.POSTGRES_SSLMODE === "require" || process.env.NODE_ENV === "production",
      };
    } catch {
      // Fallback if URL parsing fails
    }
  }

  const host = process.env.POSTGRES_HOST || "localhost";
  const isSupabase = host.includes("supabase.co") || host.includes("supabase.com");
  return {
    host,
    port: Number(process.env.POSTGRES_PORT || 5433),
    database: process.env.POSTGRES_DB || (isSupabase ? "postgres" : "sl_grid_warehouse"),
    user: process.env.POSTGRES_USER || (isSupabase ? "postgres" : "grid_analyst"),
    hasPassword: Boolean(process.env.POSTGRES_PASSWORD || process.env.DATABASE_URL),
    ssl: isSupabase || process.env.POSTGRES_SSLMODE === "require" || process.env.NODE_ENV === "production",
  };
}

/**
 * Acquire or initialize the singleton PostgreSQL client pool.
 * Dedicated strictly to read-only dashboard analysis using least-privilege role 'grid_analyst'
 * or managed Supabase PostgreSQL connection with TLS enforcement.
 */
export function getDbPool(): Pool {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL;
    const host = process.env.POSTGRES_HOST || "localhost";
    const port = Number(process.env.POSTGRES_PORT || 5433);
    const database = process.env.POSTGRES_DB || "sl_grid_warehouse";
    const user = process.env.POSTGRES_USER || "grid_analyst";
    const password = process.env.POSTGRES_PASSWORD || "";

    const isSupabase =
      (connectionString && (connectionString.includes("supabase.co") || connectionString.includes("supabase.com"))) ||
      host.includes("supabase.co") ||
      host.includes("supabase.com");

    let finalConnectionString = connectionString;
    if (connectionString && connectionString.includes("db.") && connectionString.includes(".supabase.co")) {
      try {
        const parsed = new URL(connectionString);
        const refMatch = parsed.hostname.match(/^db\.([a-z0-9]+)\.supabase\.co$/);
        if (refMatch) {
          const projectRef = refMatch[1];
          const poolerHost = process.env.SUPABASE_POOLER_HOST || "aws-0-ap-northeast-2.pooler.supabase.com";
          parsed.hostname = poolerHost;
          if (parsed.username && !parsed.username.includes(".")) {
            parsed.username = `${parsed.username}.${projectRef}`;
          }
          finalConnectionString = parsed.toString();
        }
      } catch {
        // Fall back to original connection string
      }
    }

    const useSsl = isSupabase || process.env.POSTGRES_SSLMODE === "require" || process.env.NODE_ENV === "production";
    const sslConfig = useSsl
      ? process.env.PGSSLROOTCERT
        ? { ca: process.env.PGSSLROOTCERT, rejectUnauthorized: true }
        : { rejectUnauthorized: false }
      : undefined;

    pool = new Pool({
      connectionString: finalConnectionString || undefined,
      host: finalConnectionString ? undefined : host,
      port: finalConnectionString ? undefined : port,
      database: finalConnectionString ? undefined : database,
      user: finalConnectionString ? undefined : user,
      password: finalConnectionString ? undefined : password,
      ssl: sslConfig,
      connectionTimeoutMillis: isSupabase ? 10000 : 2000,
      idleTimeoutMillis: 10000,
      max: 10,
      statement_timeout: 10000, // Enforce 10-second maximum statement execution timeout
    });

    pool.on("connect", (client) => {
      // Enforce read-only transactions at the session level as a defense-in-depth measure
      client.query("SET default_transaction_read_only = on;").catch((err) => {
        console.warn("Could not enforce read-only transaction on client connection:", err.message);
      });
    });

    pool.on("error", (err) => {
      console.warn("Unexpected error on idle PostgreSQL client pool:", err.message);
    });
  }
  return pool;
}

/**
 * Execute a read-only parameterized query against PostgreSQL.
 * Rejects destructive DDL/DML write statements and enforces statement timeouts.
 */
export async function executeQuery<T extends QueryResultRow = QueryResultRow>(
  sqlText: string,
  params: unknown[] = []
): Promise<QueryResult<T>> {
  const trimmedUpper = sqlText.trim().toUpperCase();

  // Defense-in-depth: Reject any statement starting with destructive keywords
  const destructivePrefixes = [
    "DROP ",
    "TRUNCATE ",
    "DELETE ",
    "ALTER ",
    "INSERT ",
    "UPDATE ",
    "GRANT ",
    "REVOKE ",
    "CREATE ",
  ];

  for (const prefix of destructivePrefixes) {
    if (trimmedUpper.startsWith(prefix)) {
      throw new Error(`Security violation: Operation '${prefix.trim()}' is strictly prohibited on the analytical warehouse.`);
    }
  }

  const p = getDbPool();
  return p.query<T>(sqlText, params);
}
