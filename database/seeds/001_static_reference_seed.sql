-- =============================================================================
-- Seed Script : 001_static_reference_seed.sql
-- Purpose     : Idempotent SQL verification & core unit/period baseline seed.
--               Full reference + calendar + interval + verified SL entity
--               seeding is executed via: python scripts/seed_reference.py
-- Governance  : Contains ZERO fabricated electricity or weather measurements.
-- =============================================================================

INSERT INTO ref.unit (unit_code, unit_name, unit_symbol, measurement_dimension, is_canonical_warehouse_unit, description)
VALUES
    ('MW', 'Megawatt', 'MW', 'POWER', TRUE, 'Instantaneous active electrical power or rated plant capacity (10^6 W).'),
    ('MWh', 'Megawatt-hour', 'MWh', 'ENERGY', TRUE, 'Canonical warehouse unit for integrated electrical energy.'),
    ('GWh', 'Gigawatt-hour', 'GWh', 'ENERGY', FALSE, 'Utility statistical energy unit (1 GWh = 1,000 MWh).')
ON CONFLICT (unit_code) DO NOTHING;

INSERT INTO ref.reporting_period_type (period_type_code, period_type_name, nominal_minutes, min_days, max_days, is_subdaily, description)
VALUES
    ('INTERVAL_15MIN', '15-Minute Dispatch Interval', 15, 1, 1, TRUE, 'Operational 15-minute SCADA/System Control dispatch observation.'),
    ('HOURLY', 'Hourly Interval', 60, 1, 1, TRUE, '60-minute operational dispatch or load observation.'),
    ('DAILY', 'Calendar Day', 1440, 1, 1, FALSE, 'Single SLST calendar date total or daily meteorological summary.'),
    ('MONTHLY', 'Calendar Month', NULL, 28, 31, FALSE, 'Full calendar month aggregate (28 to 31 days).'),
    ('QUARTERLY', 'Calendar Quarter', NULL, 90, 92, FALSE, 'Three-month calendar quarter aggregate.'),
    ('ANNUAL', 'Calendar Year', NULL, 365, 366, FALSE, 'Full calendar year (Jan 1 to Dec 31) total or year-end snapshot.')
ON CONFLICT (period_type_code) DO NOTHING;
