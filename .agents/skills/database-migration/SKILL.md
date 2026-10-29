---
name: database-migration
description: >-
  Provides procedures for creating, ordering, applying, rolling back, and verifying PostgreSQL database migrations.
  Use when creating new database schema migrations, verifying migration integrity, or planning database schema updates.
---

# Database Migration Skill

## When to Use This Skill
Use this skill whenever introducing schema changes, creating tables, modifying indexes, adding constraints, or validating the database bootstrap process.

## Migration Design & Execution Procedure

### Step 1: Pre-Migration Planning & Naming
1. Determine the current highest migration sequence number in `database/migrations/`.
2. Format the new migration filename:
   - `<sequence_3digits>_<descriptive_snake_case_action>.sql`
   - Example: `001_create_schema_and_tracking.sql`, `002_create_dim_date.sql`
3. NEVER modify or reorder previously applied migration files.
4. Each migration must be strictly transactional (wrapped in `BEGIN; ... COMMIT;` where supported).

### Step 2: Schema Migration Tracking Table
Ensure the migration engine maintains an audit table in PostgreSQL:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64) NOT NULL
);
```

### Step 3: Writing Forward & Rollback SQL
1. Write the forward migration in `database/migrations/<version>_<action>.sql`.
2. Provide a corresponding rollback script or verification query in `database/migrations/rollbacks/<version>_rollback.sql` or documented in the migration header.
3. Include explicit DDL:
   - Avoid destructive drops without migration backups.
   - Use `CREATE TABLE IF NOT EXISTS` or standard transactional DDL.

### Step 4: Migration Application via Python Runner
Execute migrations using the migration runner utility `scripts/migrate.py`:
```bash
python scripts/migrate.py up
```
The runner must:
- Check connection to PostgreSQL.
- Read all `.sql` files in sorted numerical order.
- Verify applied versions in `schema_migrations`.
- Calculate SHA-256 of the migration script and ensure it matches if previously recorded.
- Apply pending migrations sequentially inside a transaction.

## Expected Outputs
- Numbered SQL migration files in `database/migrations/`
- Updated `schema_migrations` records in PostgreSQL
- Migration execution log

## Verification Steps
1. Run `python scripts/migrate.py status` to confirm pending vs applied migrations.
2. Verify rollback idempotency: applying migrations, testing down, and reapplying up must succeed with zero state corruption.
3. Validate schema using PostgreSQL catalog query:
   ```sql
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
   ```
