# GridLens Phase 6.2 — Security Incident Response & GitHub Actions Recovery Checklist

## 1. Overview

This operational runbook provides the required owner actions for:
1. **GitHub Actions Runner & Billing Recovery** (resolving platform-level pre-execution failures where scheduled workflows fail before a runner is assigned).
2. **Database Credential Rotation & Least-Privilege Secret Configuration** (responding to historical credential exposure in earlier commits and configuring role-separated Supabase connections).

---

## 2. GitHub Actions Pre-Execution Failure Analysis & Owner Checklist (Phase 1 — Problem B)

### Root Cause Classification
Inspection of the scheduled workflow runs between November 6 and November 9, 2026 identified two distinct failure modes:

1. **Application / Configuration Failure (November 6, 2026 — Fixed in Code)**:
   - The runner provisioned normally, installed dependencies, and ran `python scripts/refresh_warehouse.py` without `--acquire` and with an empty `DATABASE_URL` secret.
   - `DatabaseConfig.from_env()` silently fell back to `localhost:5432/sl_grid_warehouse`, resulting in `Connection refused`.
   - **Code Fix Applied**:
     - `.github/workflows/scheduled-data-refresh.yml` now validates `DATABASE_URL` before any Python step executes and fails immediately with an actionable error if the secret is missing, empty, or points to `localhost`.
     - `scripts/refresh_warehouse.py` now runs a read-only preflight check (`verify_warehouse_preflight`) and passes `--acquire --require-remote`.

2. **Platform / Account-Level Runner Provisioning Restriction (November 7–9, 2026 — Requires Owner UI Action)**:
   - Subsequent jobs failed within 0–3 seconds with **no runner assigned** and **zero executed steps**.
   - A repository code change alone cannot bypass GitHub account-level billing holds, spending limits, or disabled Actions runner quotas.

### Required Repository Owner Actions in GitHub UI
1. **Verify Billing & Spending Limits**:
   - Navigate to **GitHub Account Settings** &rarr; **Billing and plans** &rarr; **Plans and usage**.
   - Ensure there is no payment hold, expired billing method, or `$0.00` Actions spending limit blocking `ubuntu-latest` hosted runners (even on public repositories, an account-level billing flag blocks hosted runner allocation).
2. **Verify Repository Actions Permissions**:
   - Navigate to **Repository** (`HajithMohamed/LankaGrid-Analytics`) &rarr; **Settings** &rarr; **Actions** &rarr; **General**.
   - Under **Actions permissions**, select **Allow all actions and reusable workflows**.
   - Under **Workflow permissions**, select **Read repository contents and packages permissions**.
3. **Re-Enable Scheduled Workflow If Automatically Disabled or Blocked**:
   - Navigate to **Actions** &rarr; **Scheduled Data Warehouse Refresh**.
   - If a banner indicates the workflow was disabled due to consecutive failures, click **Enable workflow**.
4. **Trigger Manual Verification Run**:
   - After configuring the `DATABASE_URL` secret (Section 3 below), click **Run workflow** (`workflow_dispatch`) on branch `fix/phase-6-scheduled-refresh-reliability` (or `development`) with `dataset: all` and verify that an `ubuntu-latest` runner starts and completes all steps.

---

## 3. Credential Rotation & Least-Privilege Secret Checklist (Phase 3)

> [!IMPORTANT]
> Removing a credential or project identifier from the latest Git commit does **not** erase it from historical Git commits. Any password that ever appeared in tracked files or commit history must be treated as compromised and rotated immediately.

### Step 1 — Rotate the Supabase Database Password
1. Sign in to the [Supabase Dashboard](https://supabase.com/dashboard) and select your GridLens project.
2. Navigate to **Project Settings** (`⚙️`) &rarr; **Database** &rarr; **Database password**.
3. Click **Reset database password**, generate a high-entropy password (at least 32 characters), and save it securely in your password manager.

### Step 2 — Rotate Role-Separated Warehouse Passwords (`grid_admin`, `grid_etl`, `grid_analyst`)
1. Open the **Supabase SQL Editor** (or connect as `postgres` via `psql` with TLS enabled) and rotate the passwords for each least-privilege role:
   ```sql
   ALTER ROLE grid_admin WITH PASSWORD '<NEW_STRONG_ADMIN_PASSWORD>';
   ALTER ROLE grid_etl WITH PASSWORD '<NEW_STRONG_ETL_PASSWORD>';
   ALTER ROLE grid_analyst WITH PASSWORD '<NEW_STRONG_ANALYST_PASSWORD>';
   ```
2. Apply migration `023` so `grid_analyst` has read-only access to `raw.source_system` and `raw.source_document` and `etl.sp_ensure_calendar_and_partitions` is active:
   ```bash
   python scripts/migrate_supabase.py --skip-data
   ```

### Step 3 — Update GitHub Actions Secrets
1. Navigate to **GitHub Repository** &rarr; **Settings** &rarr; **Secrets and variables** &rarr; **Actions**.
2. Create or update the repository secret named **`DATABASE_URL`**:
   - Use the **Session Pooler (port 5432)** connection string from **Supabase Dashboard &rarr; Connect &rarr; ORMs / Session Pooler** with the `grid_etl` (or `postgres.<project-ref>`) user:
     ```text
     postgresql://grid_etl.<project-ref>:<NEW_STRONG_ETL_PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
     ```
   - Why Session Pooler (`:5432`) for GitHub Actions? GitHub-hosted `ubuntu-latest` runners are IPv4-only by default, whereas `db.<project-ref>.supabase.co` direct connections resolve to IPv6 unless the Supabase IPv4 add-on is enabled. The Supabase Session Pooler (`aws-0-<region>.pooler.supabase.com:5432`) supports IPv4, session variables (`SET TIME ZONE`), temporary tables, and `COPY FROM STDIN`.

### Step 4 — Update Next.js Dashboard Deployment Environment Variables (Vercel)
1. In your Vercel project dashboard, navigate to **Settings** &rarr; **Environment Variables**.
2. Set **`ANALYST_DATABASE_URL`** (or **`DATABASE_URL`**) using the read-only `grid_analyst` role:
   ```text
   postgresql://grid_analyst.<project-ref>:<NEW_STRONG_ANALYST_PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require
   ```
3. Optionally set **`MONITORING_API_TOKEN`** if you wish to restrict `/api/metadata/freshness` and `/api/metadata/coverage` to bearer-authenticated monitoring requests.
4. Redeploy the production/preview deployment so the rotated credentials take effect.

### Step 5 — Verify Revocation of Old Credentials
1. Attempt a read-only connection test using the old password from a local terminal; confirm that PostgreSQL rejects authentication with `password authentication failed`.
2. Run the automated preflight check with the new credentials:
   ```bash
   python scripts/refresh_warehouse.py --preflight-only --require-remote
   ```
   Confirm output reports `Preflight OK: db=postgres, ..., ssl=True, schemas=7/7`.

