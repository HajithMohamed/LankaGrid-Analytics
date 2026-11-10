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
  const dbUrl =
    process.env.ANALYST_DATABASE_URL ||
    process.env.READONLY_DATABASE_URL ||
    process.env.DATABASE_URL;
  if (dbUrl) {
    try {
      const parsed = new URL(dbUrl);
      const isSupabase =
        parsed.hostname.includes("supabase.co") || parsed.hostname.includes("supabase.com");
      return {
        host: parsed.hostname,
        port: parsed.port ? Number(parsed.port) : 5432,
        database: parsed.pathname ? parsed.pathname.replace(/^\//, "") : "postgres",
        user: decodeURIComponent(parsed.username || "grid_analyst"),
        hasPassword: Boolean(parsed.password),
        ssl:
          isSupabase ||
          process.env.POSTGRES_SSLMODE === "require" ||
          process.env.POSTGRES_SSLMODE === "verify-full" ||
          process.env.NODE_ENV === "production",
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
    user:
      process.env.POSTGRES_ANALYST_USER ||
      process.env.POSTGRES_USER ||
      (isSupabase ? "grid_analyst" : "grid_analyst"),
    hasPassword: Boolean(
      process.env.POSTGRES_ANALYST_PASSWORD ||
        process.env.POSTGRES_PASSWORD ||
        process.env.ANALYST_DATABASE_URL ||
        process.env.DATABASE_URL
    ),
    ssl:
      isSupabase ||
      process.env.POSTGRES_SSLMODE === "require" ||
      process.env.POSTGRES_SSLMODE === "verify-full" ||
      process.env.NODE_ENV === "production",
  };
}

/**
 * Build verified TLS configuration for node-postgres.
 * Certificate verification is always enabled (rejectUnauthorized: true).
 * Optional custom CA certificate bundle can be provided via SUPABASE_CA_CERT or PGSSLROOTCERT.
 */
function buildVerifiedTlsConfig(): { rejectUnauthorized: true; ca?: string } {
  const caCert = process.env.SUPABASE_CA_CERT || process.env.PGSSLROOTCERT;
  if (caCert && caCert.trim().length > 0) {
    return {
      rejectUnauthorized: true,
      ca: caCert.includes("-----BEGIN CERTIFICATE-----")
        ? caCert
        : undefined,
    };
  }
  return { rejectUnauthorized: true };
}

/**
 * Acquire or initialize the singleton PostgreSQL client pool.
 * Dedicated strictly to read-only dashboard analysis using least-privilege role 'grid_analyst'
 * or managed Supabase PostgreSQL connection with verified TLS enforcement.
 */
export function getDbPool(): Pool {
  if (!pool) {
    const rawConnectionString =
      process.env.ANALYST_DATABASE_URL ||
      process.env.READONLY_DATABASE_URL ||
      process.env.DATABASE_URL;
    let host = process.env.POSTGRES_HOST || "localhost";
    let port = Number(process.env.POSTGRES_PORT || 5433);
    let database = process.env.POSTGRES_DB || "sl_grid_warehouse";
    let user = process.env.POSTGRES_ANALYST_USER || process.env.POSTGRES_USER || "grid_analyst";
    let password = process.env.POSTGRES_ANALYST_PASSWORD || process.env.POSTGRES_PASSWORD || "";

    if (rawConnectionString) {
      try {
        const parsed = new URL(rawConnectionString);
        host = parsed.hostname || host;
        port = parsed.port ? Number(parsed.port) : 5432;
        database = parsed.pathname ? parsed.pathname.replace(/^\//, "") : "postgres";
        user = decodeURIComponent(parsed.username || user);
        password = decodeURIComponent(parsed.password || password);

        // Optional explicit pooler override only when SUPABASE_POOLER_HOST is explicitly configured
        const explicitPoolerHost = process.env.SUPABASE_POOLER_HOST?.trim();
        if (
          explicitPoolerHost &&
          host.startsWith("db.") &&
          host.endsWith(".supabase.co")
        ) {
          const projectRef = host.split(".")[1];
          host = explicitPoolerHost;
          if (!user.includes(".")) {
            user = `${user}.${projectRef}`;
          }
        }
      } catch {
        // Fallback to raw parameters if URL is malformed
      }
    }

    const isSupabase =
      host.includes("supabase.co") || host.includes("supabase.com");

    const useSsl =
      isSupabase ||
      process.env.POSTGRES_SSLMODE === "require" ||
      process.env.POSTGRES_SSLMODE === "verify-ca" ||
      process.env.POSTGRES_SSLMODE === "verify-full" ||
      process.env.NODE_ENV === "production";

    pool = new Pool({
      host,
      port,
      database,
      user,
      password,
      ssl: useSsl ? buildVerifiedTlsConfig() : undefined,
      connectionTimeoutMillis: isSupabase ? 10000 : 2000,
      idleTimeoutMillis: 10000,
      max: 10,
      statement_timeout: Number(process.env.QUERY_STATEMENT_TIMEOUT_MS || 10000),
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
