---
trigger: always_on
description: Security standards, credential protection, and database access controls
---
# Security & Secret Management Rules

## Zero-Credential In Git Policy
- **Never commit passwords, tokens, API keys, private keys, or sensitive configuration into Git.**
- All sensitive variables must be read from environment variables or a local `.env` file that is ignored by Git (`.gitignore`).
- `.env.example` must only contain non-sensitive, safe dummy placeholders (e.g. `POSTGRES_PASSWORD=grid_dev_password_change_me`).

## Database Access Control & Connection Security
- The warehouse application must run with least privilege.
- Use explicit usernames and roles in PostgreSQL (`grid_admin` for migrations/DDL, `grid_etl` for daily loading, `grid_analyst` for read-only analytical queries).
- Prevent SQL injection vulnerabilities:
  - ALWAYS use parameterized queries with `psycopg` (e.g., `cursor.execute("SELECT * FROM dim_date WHERE date_id = %s", (date_id,))`).
  - NEVER format or concatenate raw strings into SQL queries.

## Secret Scanning & Pre-Commit Checks
- Before staging any file in Git, verify that no secret patterns (`ghp_`, `AKIA`, passwords, tokens) are present.
- If a secret is accidentally committed, it must be invalidated immediately and the commit history rewritten before pushing.
