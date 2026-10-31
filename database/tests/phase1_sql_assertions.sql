-- =============================================================================
-- SQL Integrity & Catalog Assertion Suite: phase1_sql_assertions.sql
-- Purpose : Verify schemas, tables, partitions, views, materialized views,
--           functions, procedures, triggers, roles, reference seeds, and
--           zero-fabrication production fact state in PostgreSQL 18.
-- =============================================================================

DO $$
DECLARE
    v_schema_count INT;
    v_dim_count INT;
    v_fact_count INT;
    v_partition_count INT;
    v_view_count INT;
    v_mv_count INT;
    v_fn_count INT;
    v_proc_count INT;
    v_trig_count INT;
    v_role_count INT;
    v_dq_rule_count INT;
    v_fact_rows BIGINT;
BEGIN
    -- 1. All 7 warehouse schemas exist
    SELECT COUNT(*) INTO v_schema_count
      FROM information_schema.schemata
     WHERE schema_name IN ('raw', 'staging', 'ref', 'dw', 'mart', 'audit', 'etl');
    IF v_schema_count <> 7 THEN
        RAISE EXCEPTION 'Expected 7 warehouse schemas, found %', v_schema_count;
    END IF;

    -- 2. All 9 conformed dimensions exist in dw
    SELECT COUNT(*) INTO v_dim_count
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'dw'
       AND c.relkind = 'r'
       AND c.relname LIKE 'dim_%';
    IF v_dim_count <> 9 THEN
        RAISE EXCEPTION 'Expected 9 conformed dimensions in dw, found %', v_dim_count;
    END IF;

    -- 3. All 6 parent fact tables exist in dw (5 regular + 1 partitioned parent)
    SELECT COUNT(*) INTO v_fact_count
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'dw'
       AND c.relkind IN ('r', 'p')
       AND NOT c.relispartition
       AND c.relname LIKE 'fact_%';
    IF v_fact_count <> 6 THEN
        RAISE EXCEPTION 'Expected 6 parent fact tables in dw, found %', v_fact_count;
    END IF;

    -- 4. Partitioned dispatch table has >= 5 partitions
    SELECT COUNT(*) INTO v_partition_count
      FROM pg_inherits i
      JOIN pg_class p ON p.oid = i.inhparent
      JOIN pg_namespace n ON n.oid = p.relnamespace
     WHERE n.nspname = 'dw' AND p.relname = 'fact_dispatch_interval';
    IF v_partition_count < 5 THEN
        RAISE EXCEPTION 'Expected >= 5 dispatch partitions, found %', v_partition_count;
    END IF;

    -- 5. Views & Materialized views exist
    SELECT COUNT(*) INTO v_view_count
      FROM pg_views
     WHERE schemaname IN ('mart', 'audit');
    IF v_view_count < 6 THEN
        RAISE EXCEPTION 'Expected >= 6 analytical/audit views, found %', v_view_count;
    END IF;

    SELECT COUNT(*) INTO v_mv_count
      FROM pg_matviews
     WHERE schemaname = 'mart';
    IF v_mv_count <> 3 THEN
        RAISE EXCEPTION 'Expected 3 materialized views in mart, found %', v_mv_count;
    END IF;

    -- 6. Functions, Procedures, and Triggers exist
    SELECT COUNT(*) INTO v_fn_count
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'etl' AND p.prokind = 'f';
    IF v_fn_count < 8 THEN
        RAISE EXCEPTION 'Expected >= 8 functions in etl schema, found %', v_fn_count;
    END IF;

    SELECT COUNT(*) INTO v_proc_count
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'etl' AND p.prokind = 'p';
    IF v_proc_count < 7 THEN
        RAISE EXCEPTION 'Expected >= 7 stored procedures in etl schema, found %', v_proc_count;
    END IF;

    SELECT COUNT(*) INTO v_trig_count
      FROM pg_trigger t
      JOIN pg_class c ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE NOT t.tgisinternal
       AND n.nspname IN ('ref', 'audit');
    IF v_trig_count < 13 THEN
        RAISE EXCEPTION 'Expected >= 13 user triggers in ref/audit, found %', v_trig_count;
    END IF;

    -- 7. Least-privilege roles exist
    SELECT COUNT(*) INTO v_role_count
      FROM pg_roles
     WHERE rolname IN ('grid_admin', 'grid_etl', 'grid_analyst');
    IF v_role_count <> 3 THEN
        RAISE EXCEPTION 'Expected 3 warehouse roles, found %', v_role_count;
    END IF;

    -- 8. Reference seeding verified (>= 13 DQ rules) and zero fabricated fact rows
    SELECT COUNT(*) INTO v_dq_rule_count FROM ref.data_quality_rule;
    IF v_dq_rule_count < 13 THEN
        RAISE EXCEPTION 'Expected >= 13 DQ rules seeded, found %', v_dq_rule_count;
    END IF;

    SELECT (
        (SELECT COUNT(*) FROM dw.fact_dispatch_interval)
        + (SELECT COUNT(*) FROM dw.fact_generation_period)
        + (SELECT COUNT(*) FROM dw.fact_capacity_period)
        + (SELECT COUNT(*) FROM dw.fact_electricity_sales)
        + (SELECT COUNT(*) FROM dw.fact_weather_daily)
        + (SELECT COUNT(*) FROM dw.fact_published_metric)
    ) INTO v_fact_rows;

    IF v_fact_rows <> 0 THEN
        RAISE EXCEPTION 'Production fact tables must contain 0 fabricated rows after seeding, found %', v_fact_rows;
    END IF;

    RAISE NOTICE 'ALL PHASE 1 SQL CATALOG AND INTEGRITY ASSERTIONS PASSED.';
END;
$$;

