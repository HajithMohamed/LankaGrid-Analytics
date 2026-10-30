"""
Idempotent Reference and Conformed Dimension Seeding for Phase 1.

GOVERNANCE:
- Seeds ONLY verified static domain taxonomies, calendar/time structures, official
  Sri Lankan administrative/CEB classifications, verified plant identities/aliases,
  data-quality rule definitions, and metric definitions.
- NEVER seeds fabricated generation, dispatch, demand, capacity, sales, or weather
  measurements into dw.fact_* tables.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, time, timedelta
from typing import Any

from src.common.config import DatabaseConfig
from src.common.db import get_connection

# 1. Measurement Units (ref.unit)
UNITS: list[dict[str, Any]] = [
    {
        "unit_code": "MW",
        "unit_name": "Megawatt",
        "unit_symbol": "MW",
        "measurement_dimension": "POWER",
        "is_canonical_warehouse_unit": True,
        "description": "Instantaneous active electrical power or rated plant capacity (10^6 W).",
    },
    {
        "unit_code": "kW",
        "unit_name": "Kilowatt",
        "unit_symbol": "kW",
        "measurement_dimension": "POWER",
        "is_canonical_warehouse_unit": False,
        "description": "Active electrical power (10^3 W = 0.001 MW).",
    },
    {
        "unit_code": "MWh",
        "unit_name": "Megawatt-hour",
        "unit_symbol": "MWh",
        "measurement_dimension": "ENERGY",
        "is_canonical_warehouse_unit": True,
        "description": "Canonical warehouse unit for integrated electrical energy.",
    },
    {
        "unit_code": "GWh",
        "unit_name": "Gigawatt-hour",
        "unit_symbol": "GWh",
        "measurement_dimension": "ENERGY",
        "is_canonical_warehouse_unit": False,
        "description": "Utility statistical energy unit (1 GWh = 1,000 MWh).",
    },
    {
        "unit_code": "kWh",
        "unit_name": "Kilowatt-hour",
        "unit_symbol": "kWh",
        "measurement_dimension": "ENERGY",
        "is_canonical_warehouse_unit": False,
        "description": "Retail billing energy unit (1 kWh = 0.001 MWh).",
    },
    {
        "unit_code": "MJ/m2/day",
        "unit_name": "Megajoules per square metre per day",
        "unit_symbol": "MJ/m2/d",
        "measurement_dimension": "IRRADIANCE_ENERGY",
        "is_canonical_warehouse_unit": True,
        "description": "Daily integrated solar shortwave downward irradiance (NASA POWER).",
    },
    {
        "unit_code": "kWh/m2/day",
        "unit_name": "Kilowatt-hours per square metre per day",
        "unit_symbol": "kWh/m2/d",
        "measurement_dimension": "IRRADIANCE_ENERGY",
        "is_canonical_warehouse_unit": False,
        "description": "Daily solar insolation equivalent (1 MJ/m2/day = 0.2777777778 kWh/m2/day).",
    },
    {
        "unit_code": "kW/m2",
        "unit_name": "Kilowatts per square metre",
        "unit_symbol": "kW/m2",
        "measurement_dimension": "IRRADIANCE_POWER",
        "is_canonical_warehouse_unit": False,
        "description": "Mean solar irradiance flux density.",
    },
    {
        "unit_code": "C",
        "unit_name": "Degrees Celsius",
        "unit_symbol": "degC",
        "measurement_dimension": "TEMPERATURE",
        "is_canonical_warehouse_unit": True,
        "description": "Ambient air temperature at 2 metres.",
    },
    {
        "unit_code": "mm/day",
        "unit_name": "Millimetres per day",
        "unit_symbol": "mm/d",
        "measurement_dimension": "LENGTH",
        "is_canonical_warehouse_unit": True,
        "description": "Daily bias-corrected total precipitation.",
    },
    {
        "unit_code": "m/s",
        "unit_name": "Metres per second",
        "unit_symbol": "m/s",
        "measurement_dimension": "SPEED",
        "is_canonical_warehouse_unit": True,
        "description": "Wind speed at 10m or 50m anemometer height.",
    },
    {
        "unit_code": "PCT",
        "unit_name": "Percentage",
        "unit_symbol": "%",
        "measurement_dimension": "PERCENTAGE",
        "is_canonical_warehouse_unit": True,
        "description": "Relative percentage (0 to 100) for humidity, losses, or load factor.",
    },
    {
        "unit_code": "MCM",
        "unit_name": "Million Cubic Metres",
        "unit_symbol": "MCM",
        "measurement_dimension": "VOLUME",
        "is_canonical_warehouse_unit": True,
        "description": "Hydro reservoir active water storage volume.",
    },
    {
        "unit_code": "LKR",
        "unit_name": "Sri Lankan Rupee",
        "unit_symbol": "LKR",
        "measurement_dimension": "CURRENCY",
        "is_canonical_warehouse_unit": True,
        "description": "Sri Lankan Rupees for billed revenue.",
    },
    {
        "unit_code": "MLKR",
        "unit_name": "Million Sri Lankan Rupees",
        "unit_symbol": "LKR Mn",
        "measurement_dimension": "CURRENCY",
        "is_canonical_warehouse_unit": False,
        "description": "Millions of Sri Lankan Rupees reported in CEB Statistical Digests.",
    },
    {
        "unit_code": "COUNT",
        "unit_name": "Discrete Count",
        "unit_symbol": "count",
        "measurement_dimension": "COUNT",
        "is_canonical_warehouse_unit": True,
        "description": "Discrete integer count (e.g. consumer accounts, generating units).",
    },
    {
        "unit_code": "Hz",
        "unit_name": "Hertz",
        "unit_symbol": "Hz",
        "measurement_dimension": "FREQUENCY",
        "is_canonical_warehouse_unit": True,
        "description": "Grid AC frequency (nominal 50.0 Hz in Sri Lanka).",
    },
]

# 2. Deterministic Unit Conversions (ref.unit_conversion)
UNIT_CONVERSIONS: list[dict[str, Any]] = [
    {
        "from_unit_code": "GWh",
        "to_unit_code": "MWh",
        "multiplier": "1000.0000000000",
        "additive_offset": "0",
        "requires_interval_hours": False,
        "formula_description": "MWh = GWh * 1000",
    },
    {
        "from_unit_code": "MWh",
        "to_unit_code": "GWh",
        "multiplier": "0.0010000000",
        "additive_offset": "0",
        "requires_interval_hours": False,
        "formula_description": "GWh = MWh * 0.001",
    },
    {
        "from_unit_code": "kWh",
        "to_unit_code": "MWh",
        "multiplier": "0.0010000000",
        "additive_offset": "0",
        "requires_interval_hours": False,
        "formula_description": "MWh = kWh * 0.001",
    },
    {
        "from_unit_code": "kW",
        "to_unit_code": "MW",
        "multiplier": "0.0010000000",
        "additive_offset": "0",
        "requires_interval_hours": False,
        "formula_description": "MW = kW * 0.001",
    },
    {
        "from_unit_code": "MW",
        "to_unit_code": "kW",
        "multiplier": "1000.0000000000",
        "additive_offset": "0",
        "requires_interval_hours": False,
        "formula_description": "kW = MW * 1000",
    },
    {
        "from_unit_code": "MW",
        "to_unit_code": "MWh",
        "multiplier": "1.0000000000",
        "additive_offset": "0",
        "requires_interval_hours": True,
        "formula_description": "MWh = MW * interval_hours (e.g. 0.25h for 15-min interval)",
    },
    {
        "from_unit_code": "MJ/m2/day",
        "to_unit_code": "kWh/m2/day",
        "multiplier": "0.2777777778",
        "additive_offset": "0",
        "requires_interval_hours": False,
        "formula_description": "kWh/m2/day = (MJ/m2/day) / 3.6",
    },
    {
        "from_unit_code": "kWh/m2/day",
        "to_unit_code": "MJ/m2/day",
        "multiplier": "3.6000000000",
        "additive_offset": "0",
        "requires_interval_hours": False,
        "formula_description": "MJ/m2/day = (kWh/m2/day) * 3.6",
    },
    {
        "from_unit_code": "MLKR",
        "to_unit_code": "LKR",
        "multiplier": "1000000.0000000000",
        "additive_offset": "0",
        "requires_interval_hours": False,
        "formula_description": "LKR = MLKR * 1,000,000",
    },
]

# 3. Reporting Period Types (ref.reporting_period_type)
REPORTING_PERIOD_TYPES: list[dict[str, Any]] = [
    {
        "period_type_code": "INTERVAL_15MIN",
        "period_type_name": "15-Minute Dispatch Interval",
        "nominal_minutes": 15,
        "min_days": 1,
        "max_days": 1,
        "is_subdaily": True,
        "description": "Operational 15-minute SCADA/System Control dispatch observation.",
    },
    {
        "period_type_code": "HOURLY",
        "period_type_name": "Hourly Interval",
        "nominal_minutes": 60,
        "min_days": 1,
        "max_days": 1,
        "is_subdaily": True,
        "description": "60-minute operational dispatch or load observation.",
    },
    {
        "period_type_code": "DAILY",
        "period_type_name": "Calendar Day",
        "nominal_minutes": 1440,
        "min_days": 1,
        "max_days": 1,
        "is_subdaily": False,
        "description": "Single SLST calendar date total or daily meteorological summary.",
    },
    {
        "period_type_code": "MONTHLY",
        "period_type_name": "Calendar Month",
        "nominal_minutes": None,
        "min_days": 28,
        "max_days": 31,
        "is_subdaily": False,
        "description": "Full calendar month aggregate (28 to 31 days).",
    },
    {
        "period_type_code": "QUARTERLY",
        "period_type_name": "Calendar Quarter",
        "nominal_minutes": None,
        "min_days": 90,
        "max_days": 92,
        "is_subdaily": False,
        "description": "Three-month calendar quarter aggregate.",
    },
    {
        "period_type_code": "ANNUAL",
        "period_type_name": "Calendar Year",
        "nominal_minutes": None,
        "min_days": 365,
        "max_days": 366,
        "is_subdaily": False,
        "description": "Full calendar year (Jan 1 to Dec 31) total or year-end snapshot.",
    },
]

# 4. Source Systems (raw.source_system & dw.dim_source_system)
SOURCE_SYSTEMS: list[dict[str, Any]] = [
    {
        "source_code": "CEB",
        "source_name": "CEB Statistical Digest & Corporate Publications",
        "organization_name": "Ceylon Electricity Board",
        "source_category": "UTILITY_STATISTICAL",
        "official_url": "https://ceb.lk/publication-types/statistical-digest/en",
        "default_timezone": "Asia/Colombo",
        "access_method": "PORTAL_PDF",
        "typical_granularity": "Monthly & Annual",
    },
    {
        "source_code": "PUCSL",
        "source_name": "PUCSL / CEB SCC Daily Generation & Dispatch Reports",
        "organization_name": "Public Utilities Commission of Sri Lanka",
        "source_category": "REGULATORY_OPERATIONAL",
        "official_url": "https://www.pucsl.gov.lk/daily-generation-reports-2/",
        "default_timezone": "Asia/Colombo",
        "access_method": "PORTAL_PDF",
        "typical_granularity": "15-Minute Dispatch & Daily Station Totals",
    },
    {
        "source_code": "NASA_POWER",
        "source_name": "NASA POWER Agroclimatology & Renewable Energy Dataset",
        "organization_name": "NASA Langley Research Center",
        "source_category": "SATELLITE_METEOROLOGICAL",
        "official_url": "https://power.larc.nasa.gov/api/temporal/daily/point",
        "default_timezone": "Asia/Colombo",
        "access_method": "REST_API_JSON",
        "typical_granularity": "Daily Grid Point",
    },
]

# 5. Verified Energy Sources (dw.dim_energy_source)
ENERGY_SOURCES: list[dict[str, Any]] = [
    {
        "energy_source_code": "MAJOR_HYDRO",
        "energy_category": "Hydro",
        "fuel_type": "Reservoir & Pondage Hydro",
        "reporting_classification": "Major Hydro (CEB)",
        "is_renewable": True,
        "is_dispatchable": True,
        "is_indigenous": True,
    },
    {
        "energy_source_code": "THERMAL_COAL",
        "energy_category": "Thermal Coal",
        "fuel_type": "Bituminous Coal",
        "reporting_classification": "Thermal - Coal (CEB)",
        "is_renewable": False,
        "is_dispatchable": True,
        "is_indigenous": False,
    },
    {
        "energy_source_code": "THERMAL_OIL",
        "energy_category": "Thermal Oil",
        "fuel_type": "Fuel Oil / Diesel / Naphtha",
        "reporting_classification": "Thermal - Oil (CEB & IPP)",
        "is_renewable": False,
        "is_dispatchable": True,
        "is_indigenous": False,
    },
    {
        "energy_source_code": "MINI_HYDRO",
        "energy_category": "Hydro",
        "fuel_type": "Small Run-of-River Hydro",
        "reporting_classification": "NCRE - Mini Hydro",
        "is_renewable": True,
        "is_dispatchable": False,
        "is_indigenous": True,
    },
    {
        "energy_source_code": "WIND",
        "energy_category": "Wind",
        "fuel_type": "Onshore Wind",
        "reporting_classification": "NCRE - Wind (CEB & SPP)",
        "is_renewable": True,
        "is_dispatchable": False,
        "is_indigenous": True,
    },
    {
        "energy_source_code": "SOLAR_UTILITY",
        "energy_category": "Solar",
        "fuel_type": "Ground-Mounted Solar PV",
        "reporting_classification": "NCRE - Utility Solar PV",
        "is_renewable": True,
        "is_dispatchable": False,
        "is_indigenous": True,
    },
    {
        "energy_source_code": "SOLAR_ROOFTOP",
        "energy_category": "Solar",
        "fuel_type": "Distributed Rooftop Solar PV",
        "reporting_classification": "NCRE - Rooftop Solar PV",
        "is_renewable": True,
        "is_dispatchable": False,
        "is_indigenous": True,
    },
    {
        "energy_source_code": "BIOMASS",
        "energy_category": "Biomass",
        "fuel_type": "Dendro / Agri-Residue / MSW",
        "reporting_classification": "NCRE - Biomass & Waste",
        "is_renewable": True,
        "is_dispatchable": True,
        "is_indigenous": True,
    },
    {
        "energy_source_code": "SYSTEM_AGGREGATE",
        "energy_category": "System Total",
        "fuel_type": "Multi-Source Grid Mix",
        "reporting_classification": "National Grid System Total",
        "is_renewable": False,
        "is_dispatchable": True,
        "is_indigenous": False,
    },
]

# 6. Verified Geographic & CEB Distribution Regions (dw.dim_region)
REGIONS: list[dict[str, Any]] = [
    {
        "region_code": "LK",
        "region_name": "Sri Lanka (National)",
        "region_level": "NATIONAL",
        "iso_code": "LK",
        "parent_code": None,
        "source_standard": "ISO-3166-1",
    },
    {
        "region_code": "LK-1",
        "region_name": "Western Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-1",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "LK-2",
        "region_name": "Central Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-2",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "LK-3",
        "region_name": "Southern Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-3",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "LK-4",
        "region_name": "Northern Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-4",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "LK-5",
        "region_name": "Eastern Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-5",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "LK-6",
        "region_name": "North Western Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-6",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "LK-7",
        "region_name": "North Central Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-7",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "LK-8",
        "region_name": "Uva Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-8",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "LK-9",
        "region_name": "Sabaragamuwa Province",
        "region_level": "PROVINCE",
        "iso_code": "LK-9",
        "parent_code": "LK",
        "source_standard": "ISO-3166-2:LK",
    },
    {
        "region_code": "CEB-DD1",
        "region_name": "CEB Distribution Division 1",
        "region_level": "CEB_DISTRIBUTION_REGION",
        "iso_code": None,
        "parent_code": "LK",
        "source_standard": "CEB Statistical Digest",
    },
    {
        "region_code": "CEB-DD2",
        "region_name": "CEB Distribution Division 2",
        "region_level": "CEB_DISTRIBUTION_REGION",
        "iso_code": None,
        "parent_code": "LK",
        "source_standard": "CEB Statistical Digest",
    },
    {
        "region_code": "CEB-DD3",
        "region_name": "CEB Distribution Division 3",
        "region_level": "CEB_DISTRIBUTION_REGION",
        "iso_code": None,
        "parent_code": "LK",
        "source_standard": "CEB Statistical Digest",
    },
    {
        "region_code": "CEB-DD4",
        "region_name": "CEB Distribution Division 4",
        "region_level": "CEB_DISTRIBUTION_REGION",
        "iso_code": None,
        "parent_code": "LK",
        "source_standard": "CEB Statistical Digest",
    },
]

# 7. Official Electricity Consumption / Tariff Sectors (dw.dim_consumption_sector)
CONSUMPTION_SECTORS: list[dict[str, Any]] = [
    {
        "sector_code": "DOMESTIC",
        "sector_name": "Domestic",
        "tariff_group": "Domestic",
        "is_aggregate_bucket": False,
        "source_classification": "CEB / PUCSL Tariff Schedule",
    },
    {
        "sector_code": "RELIGIOUS",
        "sector_name": "Religious & Charitable",
        "tariff_group": "Religious",
        "is_aggregate_bucket": False,
        "source_classification": "CEB / PUCSL Tariff Schedule",
    },
    {
        "sector_code": "INDUSTRIAL",
        "sector_name": "Industrial (I-1, I-2, I-3)",
        "tariff_group": "Industrial",
        "is_aggregate_bucket": False,
        "source_classification": "CEB / PUCSL Tariff Schedule",
    },
    {
        "sector_code": "GENERAL_PURPOSE",
        "sector_name": "General Purpose (GP-1, GP-2, GP-3)",
        "tariff_group": "Commercial & General",
        "is_aggregate_bucket": False,
        "source_classification": "CEB / PUCSL Tariff Schedule",
    },
    {
        "sector_code": "HOTEL",
        "sector_name": "Hotel (H-1, H-2, H-3)",
        "tariff_group": "Hotel & Tourism",
        "is_aggregate_bucket": False,
        "source_classification": "CEB / PUCSL Tariff Schedule",
    },
    {
        "sector_code": "GOVERNMENT",
        "sector_name": "Government Institutions (GV-1, GV-2, GV-3)",
        "tariff_group": "Government",
        "is_aggregate_bucket": False,
        "source_classification": "CEB / PUCSL Tariff Schedule",
    },
    {
        "sector_code": "STREET_LIGHTING",
        "sector_name": "Street Lighting",
        "tariff_group": "Public Lighting",
        "is_aggregate_bucket": False,
        "source_classification": "CEB Statistical Digest",
    },
    {
        "sector_code": "BULK_LECO",
        "sector_name": "Bulk Supply to LECO",
        "tariff_group": "Distribution Bulk",
        "is_aggregate_bucket": False,
        "source_classification": "CEB Statistical Digest",
    },
    {
        "sector_code": "AGRICULTURE",
        "sector_name": "Agriculture Tariff",
        "tariff_group": "Agriculture",
        "is_aggregate_bucket": False,
        "source_classification": "CEB Statistical Digest 2024",
    },
    {
        "sector_code": "ALL_SECTORS",
        "sector_name": "All Consumer Sectors Combined",
        "tariff_group": "Aggregate Total",
        "is_aggregate_bucket": True,
        "source_classification": "CEB Provincial Sales Summary",
    },
]

# 8. Verified Sri Lankan Power Stations & Reporting Entities (dw.dim_power_plant)
POWER_PLANTS: list[dict[str, Any]] = [
    {
        "plant_code": "VICTORIA",
        "plant_name": "Victoria",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Mahaweli",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "KOTMALE",
        "plant_name": "Kotmale",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Mahaweli",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "UPPER_KOTMALE",
        "plant_name": "Upper Kotmale",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Mahaweli",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "RANDENIGALA",
        "plant_name": "Randenigala",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Mahaweli",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "RANTAMBE",
        "plant_name": "Rantambe",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Mahaweli",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "UKUWELA",
        "plant_name": "Ukuwela",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Mahaweli",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "BOWATENNA",
        "plant_name": "Bowatenna",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Mahaweli",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "NEW_LAXAPANA",
        "plant_name": "New Laxapana",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Laxapana",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "OLD_LAXAPANA",
        "plant_name": "Old Laxapana",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Laxapana",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "CANYON",
        "plant_name": "Canyon",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Laxapana",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "WIMALASURENDRA",
        "plant_name": "Wimalasurendra",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Laxapana",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "POLPITIYA",
        "plant_name": "Polpitiya",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-2",
        "hydro_complex": "Laxapana",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "BROADLANDS",
        "plant_name": "Broadlands",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-9",
        "hydro_complex": "Laxapana",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "SAMANALAWEWA",
        "plant_name": "Samanalawewa",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-9",
        "hydro_complex": "Samanala",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "KUKULE_GANGA",
        "plant_name": "Kukule Ganga",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-9",
        "hydro_complex": "Samanala",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "UMA_OYA",
        "plant_name": "Uma Oya",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "MAJOR_HYDRO",
        "region_code": "LK-8",
        "hydro_complex": "Other Hydro",
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "LAKVIJAYA_COAL",
        "plant_name": "Lakvijaya Power Station",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_COAL",
        "region_code": "LK-6",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "LAKVIJAYA_U1",
        "plant_name": "Lakvijaya Unit 1",
        "entity_level": "UNIT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_COAL",
        "region_code": "LK-6",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "LAKVIJAYA_U2",
        "plant_name": "Lakvijaya Unit 2",
        "entity_level": "UNIT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_COAL",
        "region_code": "LK-6",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "LAKVIJAYA_U3",
        "plant_name": "Lakvijaya Unit 3",
        "entity_level": "UNIT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_COAL",
        "region_code": "LK-6",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "KELANITISSA_CCGT",
        "plant_name": "Kelanitissa Combined Cycle",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "SAPUGASKANDA_A",
        "plant_name": "Sapugaskanda Diesel A",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "SAPUGASKANDA_B",
        "plant_name": "Sapugaskanda Diesel B",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "YUGADANAVI",
        "plant_name": "West Coast (Yugadanavi)",
        "entity_level": "PLANT",
        "operator_type": "IPP",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "SOBADHANAVI",
        "plant_name": "Sobadhanavi Combined Cycle",
        "entity_level": "PLANT",
        "operator_type": "IPP",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "UTHURU_JANANI",
        "plant_name": "Uthuru Janani Power Station",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-4",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "BARGE",
        "plant_name": "Colombo Harbour Barge-Mounted Plant",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "ACE_EMBILI",
        "plant_name": "Ace Power Embilipitiya",
        "entity_level": "PLANT",
        "operator_type": "IPP",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-9",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "ACE_MATARA",
        "plant_name": "Ace Power Matara",
        "entity_level": "PLANT",
        "operator_type": "IPP",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-3",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "KELANITISSA_CCGT_S2",
        "plant_name": "Kelanitissa Combined Cycle Stage 2",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "KELANITISSA_GT7",
        "plant_name": "Kelanitissa Gas Turbine 7",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "KELANITISSA_GT_SMALL",
        "plant_name": "Kelanitissa Small Gas Turbines",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "MATUGAMA_DPP",
        "plant_name": "Matugama Diesel Power Plant",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-1",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "HAMBANTOTA_DPP",
        "plant_name": "Hambantota Diesel Power Plant",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "THERMAL_OIL",
        "region_code": "LK-3",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "MANNAR_WIND",
        "plant_name": "Thambapavani (Mannar Wind)",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "WIND",
        "region_code": "LK-4",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "HAMBANTOTA_SOLAR",
        "plant_name": "Baruthankanda (Hambantota Solar)",
        "entity_level": "PLANT",
        "operator_type": "CEB",
        "energy_source_code": "SOLAR_UTILITY",
        "region_code": "LK-3",
        "hydro_complex": None,
        "verification_status": "VERIFIED",
    },
    {
        "plant_code": "AGG_MINI_HYDRO",
        "plant_name": "Mini Hydro (Reported Aggregate)",
        "entity_level": "AGGREGATE_CATEGORY",
        "operator_type": "AGGREGATE",
        "energy_source_code": "MINI_HYDRO",
        "region_code": "LK",
        "hydro_complex": None,
        "verification_status": "AGGREGATE_REPORTED",
    },
    {
        "plant_code": "AGG_SOLAR_UTILITY",
        "plant_name": "Solar PV (Reported Aggregate)",
        "entity_level": "AGGREGATE_CATEGORY",
        "operator_type": "AGGREGATE",
        "energy_source_code": "SOLAR_UTILITY",
        "region_code": "LK",
        "hydro_complex": None,
        "verification_status": "AGGREGATE_REPORTED",
    },
    {
        "plant_code": "AGG_WIND_SPP",
        "plant_name": "SPP Wind (Reported Aggregate)",
        "entity_level": "AGGREGATE_CATEGORY",
        "operator_type": "AGGREGATE",
        "energy_source_code": "WIND",
        "region_code": "LK",
        "hydro_complex": None,
        "verification_status": "AGGREGATE_REPORTED",
    },
    {
        "plant_code": "AGG_BIOMASS",
        "plant_name": "Biomass (Reported Aggregate)",
        "entity_level": "AGGREGATE_CATEGORY",
        "operator_type": "AGGREGATE",
        "energy_source_code": "BIOMASS",
        "region_code": "LK",
        "hydro_complex": None,
        "verification_status": "AGGREGATE_REPORTED",
    },
    {
        "plant_code": "AGG_SYSTEM_TOTAL",
        "plant_name": "National Grid System Total",
        "entity_level": "AGGREGATE_CATEGORY",
        "operator_type": "AGGREGATE",
        "energy_source_code": "SYSTEM_AGGREGATE",
        "region_code": "LK",
        "hydro_complex": None,
        "verification_status": "AGGREGATE_REPORTED",
    },
]

# 9. Verified Reference Aliases & Mappings (ref.*)
PLANT_ALIASES: list[dict[str, Any]] = [
    {
        "source_code": "PUCSL",
        "alias_name": "Sapu A",
        "canonical_plant_code": "SAPUGASKANDA_A",
        "verification_status": "VERIFIED",
        "verification_evidence": "Confirmed abbreviation in PUCSL/CEB SCC Daily Generation Report thermal table (80 MW station).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Sapu B",
        "canonical_plant_code": "SAPUGASKANDA_B",
        "verification_status": "VERIFIED",
        "verification_evidence": "Confirmed abbreviation in PUCSL/CEB SCC Daily Generation Report thermal table (72 MW station).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "KCCP",
        "canonical_plant_code": "KELANITISSA_CCGT",
        "verification_status": "VERIFIED",
        "verification_evidence": "Standard CEB System Control acronym for Kelanitissa Combined Cycle Power Plant (165 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Mannar Wind Farm",
        "canonical_plant_code": "MANNAR_WIND",
        "verification_status": "VERIFIED",
        "verification_evidence": "CEB Thambapavani 100 MW Wind Power Plant on Mannar Island.",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Hambantota Solar",
        "canonical_plant_code": "HAMBANTOTA_SOLAR",
        "verification_status": "VERIFIED",
        "verification_evidence": "Baruthankanda solar park in Hambantota reported in CEB/PUCSL bulletins.",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Canyon",
        "canonical_plant_code": "CANYON",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 station row Canyon (60 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "WPS",
        "canonical_plant_code": "WIMALASURENDRA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Wimalasurendra (50 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Olax",
        "canonical_plant_code": "OLD_LAXAPANA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Old Laxapana (54 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Nlax",
        "canonical_plant_code": "NEW_LAXAPANA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for New Laxapana (100 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Polp",
        "canonical_plant_code": "POLPITIYA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Polpitiya (90 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Broadlands",
        "canonical_plant_code": "BROADLANDS",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 station row Broadlands (35 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Upper Kothmale",
        "canonical_plant_code": "UPPER_KOTMALE",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 station row Upper Kotmale (150 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Koth",
        "canonical_plant_code": "KOTMALE",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Kotmale (201 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Vict",
        "canonical_plant_code": "VICTORIA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Victoria (210 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Rand",
        "canonical_plant_code": "RANDENIGALA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Randenigala (126 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Rant",
        "canonical_plant_code": "RANTAMBE",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Rantembe (52 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Uku",
        "canonical_plant_code": "UKUWELA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Ukuwela (38 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Bowa",
        "canonical_plant_code": "BOWATENNA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Bowatenna (40 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Sam",
        "canonical_plant_code": "SAMANALAWEWA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Samanalawewa (124 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Kukule",
        "canonical_plant_code": "KUKULE_GANGA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 standard abbreviation for Kukule Ganga (70 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Uma Oya",
        "canonical_plant_code": "UMA_OYA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 station row Uma Oya (120 MW hydro).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "LVPS 1",
        "canonical_plant_code": "LAKVIJAYA_U1",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for Lakvijaya Coal Unit 1 (300 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "LVPS 2",
        "canonical_plant_code": "LAKVIJAYA_U2",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for Lakvijaya Coal Unit 2 (300 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "LVPS 3",
        "canonical_plant_code": "LAKVIJAYA_U3",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for Lakvijaya Coal Unit 3 (300 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "WCP",
        "canonical_plant_code": "YUGADANAVI",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for West Coast Power (Yugadanavi 270 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Uthuru Janani",
        "canonical_plant_code": "UTHURU_JANANI",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 station row Uthuru Janani (24 MW thermal).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Barge",
        "canonical_plant_code": "BARGE",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 station row Barge-Mounted Plant (60 MW thermal).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "ACE Embili",
        "canonical_plant_code": "ACE_EMBILI",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 station row Ace Power Embilipitiya (100 MW thermal).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "ACE Matara",
        "canonical_plant_code": "ACE_MATARA",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 station row Ace Power Matara (24 MW thermal).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "KCCPS2",
        "canonical_plant_code": "KELANITISSA_CCGT_S2",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for Kelanitissa CCGT Stage 2 (165 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "KPS(GT7)",
        "canonical_plant_code": "KELANITISSA_GT7",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for Kelanitissa Gas Turbine 7 (115 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "KPS(GT)",
        "canonical_plant_code": "KELANITISSA_GT_SMALL",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for Kelanitissa Small GTs (80 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "KPS_DPP_MATU",
        "canonical_plant_code": "MATUGAMA_DPP",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for Matugama Diesel Power Plant (20 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "KPS_DPP_HAMBA",
        "canonical_plant_code": "HAMBANTOTA_DPP",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 abbreviation for Hambantota Diesel Power Plant (20 MW).",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Solar**",
        "canonical_plant_code": "AGG_SOLAR_UTILITY",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 telemetered solar aggregate row.",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Wind **",
        "canonical_plant_code": "AGG_WIND_SPP",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 telemetered wind aggregate row.",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "BMP**",
        "canonical_plant_code": "AGG_BIOMASS",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 biomass/waste aggregate row.",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "CEB/IPP Mini Hydro***",
        "canonical_plant_code": "AGG_MINI_HYDRO",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 mini hydro aggregate row.",
        "verified_by": "db_architect",
    },
    {
        "source_code": "PUCSL",
        "alias_name": "Total MW ****",
        "canonical_plant_code": "AGG_SYSTEM_TOTAL",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL 15-Minute Dispatch Report 2024 national grid system total row.",
        "verified_by": "db_architect",
    },
]

ENERGY_SOURCE_MAPPINGS: list[dict[str, Any]] = [
    {
        "source_code": "PUCSL",
        "raw_source_label": "Major Hydro",
        "canonical_energy_source_code": "MAJOR_HYDRO",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL Daily Generation Report primary hydro summary row.",
    },
    {
        "source_code": "PUCSL",
        "raw_source_label": "Thermal Coal",
        "canonical_energy_source_code": "THERMAL_COAL",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL Daily Generation Report Lakvijaya coal summary row.",
    },
    {
        "source_code": "PUCSL",
        "raw_source_label": "Thermal Oil",
        "canonical_energy_source_code": "THERMAL_OIL",
        "verification_status": "VERIFIED",
        "verification_evidence": "PUCSL Daily Generation Report CEB + IPP fuel oil/diesel summary.",
    },
    {
        "source_code": "CEB",
        "raw_source_label": "CEB Hydro",
        "canonical_energy_source_code": "MAJOR_HYDRO",
        "verification_status": "VERIFIED",
        "verification_evidence": "CEB Statistical Digest generation by source table.",
    },
    {
        "source_code": "CEB",
        "raw_source_label": "Mini Hydro (NCRE)",
        "canonical_energy_source_code": "MINI_HYDRO",
        "verification_status": "VERIFIED",
        "verification_evidence": "CEB Statistical Digest NCRE breakdown.",
    },
]

REGION_ALIASES: list[dict[str, Any]] = [
    {
        "source_code": "CEB",
        "alias_name": "Western",
        "canonical_region_code": "LK-1",
        "verification_status": "VERIFIED",
        "verification_evidence": "ISO-3166-2:LK Western Province.",
    },
    {
        "source_code": "CEB",
        "alias_name": "Central",
        "canonical_region_code": "LK-2",
        "verification_status": "VERIFIED",
        "verification_evidence": "ISO-3166-2:LK Central Province.",
    },
    {
        "source_code": "CEB",
        "alias_name": "Distribution Region 1",
        "canonical_region_code": "CEB-DD1",
        "verification_status": "VERIFIED",
        "verification_evidence": "CEB Statistical Digest Distribution Division 1.",
    },
]

# 10. Verified Meteorological Locations (dw.dim_weather_location)
WEATHER_LOCATIONS: list[dict[str, Any]] = [
    {
        "location_code": "LOC_VICTORIA_CATCHMENT",
        "location_name": "Victoria / Mahaweli Hydro Catchment",
        "energy_zone_type": "HYDRO_CATCHMENT",
        "region_code": "LK-2",
        "latitude_deg": 7.24000,
        "longitude_deg": 80.78500,
        "elevation_m": 440.0,
    },
    {
        "location_code": "LOC_LAXAPANA_CATCHMENT",
        "location_name": "Castlereagh / Laxapana Hydro Catchment",
        "energy_zone_type": "HYDRO_CATCHMENT",
        "region_code": "LK-2",
        "latitude_deg": 6.89000,
        "longitude_deg": 80.52000,
        "elevation_m": 1100.0,
    },
    {
        "location_code": "LOC_MANNAR_WIND",
        "location_name": "Mannar Island Wind Corridor",
        "energy_zone_type": "WIND_CORRIDOR",
        "region_code": "LK-4",
        "latitude_deg": 8.98000,
        "longitude_deg": 79.90000,
        "elevation_m": 8.0,
    },
    {
        "location_code": "LOC_PUTTALAM_COAL",
        "location_name": "Norochcholai / Puttalam Coastal Corridor",
        "energy_zone_type": "THERMAL_HUB",
        "region_code": "LK-6",
        "latitude_deg": 8.01500,
        "longitude_deg": 79.72000,
        "elevation_m": 10.0,
    },
    {
        "location_code": "LOC_HAMBANTOTA_SOLAR",
        "location_name": "Hambantota Dry-Zone Solar Hub",
        "energy_zone_type": "SOLAR_HUB",
        "region_code": "LK-3",
        "latitude_deg": 6.22000,
        "longitude_deg": 81.12000,
        "elevation_m": 32.0,
    },
    {
        "location_code": "LOC_COLOMBO_LOAD",
        "location_name": "Colombo / Kelanitissa Load & Thermal Hub",
        "energy_zone_type": "LOAD_CENTER",
        "region_code": "LK-1",
        "latitude_deg": 6.95500,
        "longitude_deg": 79.88000,
        "elevation_m": 12.0,
    },
]

# 11. Canonical Metric Dictionary (dw.dim_metric)
METRICS: list[dict[str, Any]] = [
    {
        "metric_code": "PLANT_DISPATCH_MW",
        "metric_name": "Plant Active Dispatch Power",
        "business_domain": "DISPATCH",
        "measurement_class": "POWER",
        "canonical_unit_code": "MW",
        "generation_boundary": "GROSS",
        "value_nature": "REPORTED",
        "aggregation_behavior": "AVG",
        "is_summable_across_time": False,
        "is_summable_across_entities": True,
        "comparability_group": "ACTIVE_POWER_MW",
        "definition_notes": "Instantaneous/interval mean active power output in MW; summable across simultaneous plants, NEVER summable across time.",
    },
    {
        "metric_code": "SYSTEM_DEMAND_MW",
        "metric_name": "National Grid System Demand",
        "business_domain": "DISPATCH",
        "measurement_class": "POWER",
        "canonical_unit_code": "MW",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "REPORTED",
        "aggregation_behavior": "MAX",
        "is_summable_across_time": False,
        "is_summable_across_entities": False,
        "comparability_group": "SYSTEM_DEMAND_MW",
        "definition_notes": "Instantaneous grid-metered system demand in MW; distinct from billed electricity sales.",
    },
    {
        "metric_code": "SYSTEM_PEAK_DEMAND_MW",
        "metric_name": "Recorded Peak Demand",
        "business_domain": "DISPATCH",
        "measurement_class": "POWER",
        "canonical_unit_code": "MW",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "REPORTED",
        "aggregation_behavior": "MAX",
        "is_summable_across_time": False,
        "is_summable_across_entities": False,
        "comparability_group": "SYSTEM_DEMAND_MW",
        "definition_notes": "Maximum recorded national demand (night or day peak) during the reporting period.",
    },
    {
        "metric_code": "GROSS_GENERATION_MWH",
        "metric_name": "Gross Electricity Generation",
        "business_domain": "GENERATION",
        "measurement_class": "ENERGY",
        "canonical_unit_code": "MWh",
        "generation_boundary": "GROSS",
        "value_nature": "REPORTED",
        "aggregation_behavior": "SUM",
        "is_summable_across_time": True,
        "is_summable_across_entities": True,
        "comparability_group": "GROSS_ENERGY_MWH",
        "definition_notes": "Integrated electrical energy measured at generator terminals prior to station auxiliary deduction.",
    },
    {
        "metric_code": "NET_GENERATION_MWH",
        "metric_name": "Net Electricity Generation Sent Out",
        "business_domain": "GENERATION",
        "measurement_class": "ENERGY",
        "canonical_unit_code": "MWh",
        "generation_boundary": "NET",
        "value_nature": "REPORTED",
        "aggregation_behavior": "SUM",
        "is_summable_across_time": True,
        "is_summable_across_entities": True,
        "comparability_group": "NET_ENERGY_MWH",
        "definition_notes": "Electrical energy delivered to the transmission grid after deducting station auxiliary consumption; do not mix with gross.",
    },
    {
        "metric_code": "INSTALLED_CAPACITY_MW",
        "metric_name": "Installed Nameplate Capacity",
        "business_domain": "CAPACITY",
        "measurement_class": "CAPACITY",
        "canonical_unit_code": "MW",
        "generation_boundary": "GROSS",
        "value_nature": "REPORTED",
        "aggregation_behavior": "SEMI_ADDITIVE_PERIOD_END",
        "is_summable_across_time": False,
        "is_summable_across_entities": True,
        "comparability_group": "INSTALLED_CAP_MW",
        "definition_notes": "Rated generator nameplate capacity in MW; semi-additive across distinct plants at a point in time, never across time.",
    },
    {
        "metric_code": "DEPENDABLE_CAPACITY_MW",
        "metric_name": "Effective / Dependable Capacity",
        "business_domain": "CAPACITY",
        "measurement_class": "CAPACITY",
        "canonical_unit_code": "MW",
        "generation_boundary": "NET",
        "value_nature": "REPORTED",
        "aggregation_behavior": "SEMI_ADDITIVE_PERIOD_END",
        "is_summable_across_time": False,
        "is_summable_across_entities": True,
        "comparability_group": "DEPENDABLE_CAP_MW",
        "definition_notes": "Available dependable capacity in MW accounting for derating; <= installed capacity.",
    },
    {
        "metric_code": "ELECTRICITY_SALES_MWH",
        "metric_name": "Billed Electricity Sales",
        "business_domain": "SALES",
        "measurement_class": "ENERGY",
        "canonical_unit_code": "MWh",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "AUDITED_FINAL",
        "aggregation_behavior": "SUM",
        "is_summable_across_time": True,
        "is_summable_across_entities": True,
        "comparability_group": "BILLED_SALES_MWH",
        "definition_notes": "Metered and billed end-consumer energy sales (net of T&D losses); distinct from generation and demand.",
    },
    {
        "metric_code": "TD_LOSS_PCT",
        "metric_name": "Transmission & Distribution Loss Percentage",
        "business_domain": "LOSSES",
        "measurement_class": "PERCENTAGE",
        "canonical_unit_code": "PCT",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "AUDITED_FINAL",
        "aggregation_behavior": "NON_ADDITIVE",
        "is_summable_across_time": False,
        "is_summable_across_entities": False,
        "comparability_group": "LOSS_RATIO",
        "definition_notes": "Non-additive system loss percentage; must be recomputed from net generation and billed sales rather than summed.",
    },
    {
        "metric_code": "SOLAR_IRRADIANCE_SW_DWN",
        "metric_name": "All-Sky Surface Shortwave Downward Irradiance",
        "business_domain": "WEATHER",
        "measurement_class": "METEOROLOGICAL",
        "canonical_unit_code": "MJ/m2/day",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "ESTIMATED",
        "aggregation_behavior": "AVG",
        "is_summable_across_time": True,
        "is_summable_across_entities": False,
        "comparability_group": "SOLAR_IRRADIANCE",
        "definition_notes": "NASA POWER ALLSKY_SFC_SW_DWN daily incident solar radiation.",
    },
    {
        "metric_code": "AIR_TEMP_2M_C",
        "metric_name": "2-Metre Air Temperature",
        "business_domain": "WEATHER",
        "measurement_class": "METEOROLOGICAL",
        "canonical_unit_code": "C",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "ESTIMATED",
        "aggregation_behavior": "AVG",
        "is_summable_across_time": False,
        "is_summable_across_entities": False,
        "comparability_group": "AMBIENT_TEMP",
        "definition_notes": "NASA POWER T2M daily mean air temperature at 2m.",
    },
    {
        "metric_code": "PRECIPITATION_DAILY_MM",
        "metric_name": "Bias-Corrected Daily Precipitation",
        "business_domain": "WEATHER",
        "measurement_class": "METEOROLOGICAL",
        "canonical_unit_code": "mm/day",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "ESTIMATED",
        "aggregation_behavior": "SUM",
        "is_summable_across_time": True,
        "is_summable_across_entities": False,
        "comparability_group": "PRECIPITATION",
        "definition_notes": "NASA POWER PRECTOTCORR daily precipitation total in mm/day.",
    },
    {
        "metric_code": "WIND_SPEED_10M_MS",
        "metric_name": "10-Metre Wind Speed",
        "business_domain": "WEATHER",
        "measurement_class": "METEOROLOGICAL",
        "canonical_unit_code": "m/s",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "ESTIMATED",
        "aggregation_behavior": "AVG",
        "is_summable_across_time": False,
        "is_summable_across_entities": False,
        "comparability_group": "WIND_SPEED",
        "definition_notes": "NASA POWER WS10M daily mean wind speed at 10m.",
    },
    {
        "metric_code": "REL_HUMIDITY_2M_PCT",
        "metric_name": "2-Metre Relative Humidity",
        "business_domain": "WEATHER",
        "measurement_class": "METEOROLOGICAL",
        "canonical_unit_code": "PCT",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "ESTIMATED",
        "aggregation_behavior": "AVG",
        "is_summable_across_time": False,
        "is_summable_across_entities": False,
        "comparability_group": "HUMIDITY",
        "definition_notes": "NASA POWER RH2M daily relative humidity percentage.",
    },
    {
        "metric_code": "WIND_SPEED_50M_MS",
        "metric_name": "50-Metre Wind Speed",
        "business_domain": "WEATHER",
        "measurement_class": "METEOROLOGICAL",
        "canonical_unit_code": "m/s",
        "generation_boundary": "NOT_APPLICABLE",
        "value_nature": "ESTIMATED",
        "aggregation_behavior": "AVG",
        "is_summable_across_time": False,
        "is_summable_across_entities": False,
        "comparability_group": "WIND_SPEED",
        "definition_notes": "NASA POWER WS50M daily mean wind speed at hub height (50m).",
    },
]

METRIC_MAPPINGS: list[dict[str, Any]] = [
    {
        "source_code": "NASA_POWER",
        "source_field_name": "ALLSKY_SFC_SW_DWN",
        "canonical_metric_code": "SOLAR_IRRADIANCE_SW_DWN",
        "source_unit_code": "MJ/m2/day",
        "verification_status": "VERIFIED",
        "notes": "NASA POWER agroclimatology/RE parameter.",
    },
    {
        "source_code": "NASA_POWER",
        "source_field_name": "T2M",
        "canonical_metric_code": "AIR_TEMP_2M_C",
        "source_unit_code": "C",
        "verification_status": "VERIFIED",
        "notes": "NASA POWER 2m mean air temperature.",
    },
    {
        "source_code": "NASA_POWER",
        "source_field_name": "PRECTOTCORR",
        "canonical_metric_code": "PRECIPITATION_DAILY_MM",
        "source_unit_code": "mm/day",
        "verification_status": "VERIFIED",
        "notes": "NASA POWER MERRA-2 bias-corrected precipitation.",
    },
    {
        "source_code": "NASA_POWER",
        "source_field_name": "WS10M",
        "canonical_metric_code": "WIND_SPEED_10M_MS",
        "source_unit_code": "m/s",
        "verification_status": "VERIFIED",
        "notes": "NASA POWER 10m wind speed.",
    },
    {
        "source_code": "NASA_POWER",
        "source_field_name": "WS50M",
        "canonical_metric_code": "WIND_SPEED_50M_MS",
        "source_unit_code": "m/s",
        "verification_status": "VERIFIED",
        "notes": "NASA POWER 50m wind speed at hub height.",
    },
    {
        "source_code": "NASA_POWER",
        "source_field_name": "RH2M",
        "canonical_metric_code": "REL_HUMIDITY_2M_PCT",
        "source_unit_code": "PCT",
        "verification_status": "VERIFIED",
        "notes": "NASA POWER 2m relative humidity.",
    },
    {
        "source_code": "PUCSL",
        "source_field_name": "daily_generation_mwh",
        "canonical_metric_code": "GROSS_GENERATION_MWH",
        "source_unit_code": "MWh",
        "verification_status": "VERIFIED",
        "notes": "PUCSL Daily Generation Report station output.",
    },
    {
        "source_code": "CEB",
        "source_field_name": "sales_gwh",
        "canonical_metric_code": "ELECTRICITY_SALES_MWH",
        "source_unit_code": "GWh",
        "verification_status": "VERIFIED",
        "notes": "CEB Statistical Digest tariff sales converted 1 GWh = 1,000 MWh.",
    },
]

# 12. All 13 Data Quality Rule Classifications (ref.data_quality_rule)
DATA_QUALITY_RULES: list[dict[str, Any]] = [
    {
        "rule_code": "DQ_GEN_MISSING_ENERGY",
        "rule_name": "Missing Generation Measurement",
        "issue_classification": "MISSING_VALUE",
        "target_domain": "GENERATION",
        "default_severity": "WARNING",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "parsed_generation_value IS NULL or matches sentinel ('-', 'N/A', '-999'). Never impute as 0.",
    },
    {
        "rule_code": "DQ_EXACT_OR_GRAIN_DUPLICATE",
        "rule_name": "Duplicate Source or Grain Record",
        "issue_classification": "DUPLICATE",
        "target_domain": "ALL",
        "default_severity": "ERROR",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "Duplicate record detected for identical (entity, period, metric, source, revision).",
    },
    {
        "rule_code": "DQ_NUMERIC_TYPE_PARSE_ERROR",
        "rule_name": "Non-Numeric Measurement Token",
        "issue_classification": "INCORRECT_DATA_TYPE",
        "target_domain": "ALL",
        "default_severity": "ERROR",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "Measurement text is neither a valid numeric literal nor a registered missing-value sentinel.",
    },
    {
        "rule_code": "DQ_GEN_NEGATIVE_OUTPUT",
        "rule_name": "Impossible Negative Generation or Power",
        "issue_classification": "INVALID_MEASUREMENT",
        "target_domain": "GENERATION",
        "default_severity": "ERROR",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "Active power or energy < 0 for non-pumping/non-auxiliary generation entity.",
    },
    {
        "rule_code": "DQ_STATISTICAL_IQR_ZSCORE",
        "rule_name": "Statistical Distribution Outlier",
        "issue_classification": "STATISTICAL_OUTLIER",
        "target_domain": "DISPATCH",
        "default_severity": "WARNING",
        "blocks_warehouse_load": False,
        "rule_expression_summary": "Observation exceeds plant rated capacity * 1.05 or falls outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR].",
    },
    {
        "rule_code": "DQ_UNIT_DIMENSIONAL_MISMATCH",
        "rule_name": "Incompatible Unit Conversion",
        "issue_classification": "UNIT_INCONSISTENCY",
        "target_domain": "ALL",
        "default_severity": "CRITICAL",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "Reported unit does not match metric dimension (e.g. MW supplied for energy without interval duration).",
    },
    {
        "rule_code": "DQ_PLANT_NAMING_VARIANT",
        "rule_name": "Unverified Station Alias Variant",
        "issue_classification": "NAMING_INCONSISTENCY",
        "target_domain": "GENERATION",
        "default_severity": "WARNING",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "Source plant spelling differs from canonical name and lacks VERIFIED ref.plant_alias entry.",
    },
    {
        "rule_code": "DQ_DISPATCH_MISSING_SLOT",
        "rule_name": "Missing 15-Minute Dispatch Interval",
        "issue_classification": "MISSING_REPORTING_INTERVAL",
        "target_domain": "DISPATCH",
        "default_severity": "WARNING",
        "blocks_warehouse_load": False,
        "rule_expression_summary": "Daily 15-minute dispatch profile contains fewer than expected 96 SLST intervals.",
    },
    {
        "rule_code": "DQ_DIM_UNMATCHED_ENTITY",
        "rule_name": "Unmatched Conformed Dimension Key",
        "issue_classification": "UNMATCHED_DIMENSION",
        "target_domain": "ALL",
        "default_severity": "ERROR",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "Natural business key cannot be resolved to an active conformed dimension surrogate key.",
    },
    {
        "rule_code": "DQ_CROSS_SOURCE_VARIANCE",
        "rule_name": "Conflicting CEB vs PUCSL Published Value",
        "issue_classification": "CONFLICTING_SOURCE_VALUE",
        "target_domain": "RECONCILIATION",
        "default_severity": "WARNING",
        "blocks_warehouse_load": False,
        "rule_expression_summary": "Percentage variance between compatible CEB and PUCSL aggregates exceeds configured tolerance.",
    },
    {
        "rule_code": "DQ_PERIOD_GRANULARITY_MISMATCH",
        "rule_name": "Incompatible Reporting Granularity",
        "issue_classification": "INCOMPATIBLE_REPORTING_GRANULARITY",
        "target_domain": "ALL",
        "default_severity": "CRITICAL",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "Start and end dates violate declared period_type_code (e.g. annual span tagged as DAILY).",
    },
    {
        "rule_code": "DQ_UNSUPPORTED_CAPACITY_FACTOR",
        "rule_name": "Unsupported Derived Calculation",
        "issue_classification": "UNSUPPORTED_CALCULATION",
        "target_domain": "CAPACITY",
        "default_severity": "ERROR",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "Attempted capacity factor or loss derivation across incompatible time spans or gross/net boundaries.",
    },
    {
        "rule_code": "DQ_PDF_TABLE_PARSE_FAILURE",
        "rule_name": "Document Table Extraction Failure",
        "issue_classification": "PARSING_FAILURE",
        "target_domain": "INGESTION",
        "default_severity": "CRITICAL",
        "blocks_warehouse_load": True,
        "rule_expression_summary": "PDF/XLSX table structure failed row/column checksum or structural schema parsing.",
    },
]

# 13. Source Precedence Rules (ref.source_precedence)
SOURCE_PRECEDENCE: list[dict[str, Any]] = [
    {
        "business_domain": "DISPATCH",
        "period_type_code": "INTERVAL_15MIN",
        "authoritative_source_code": "PUCSL",
        "secondary_source_code": "CEB",
        "precedence_rank": 1,
        "rationale": "PUCSL / CEB System Control Daily Generation Reports provide the official 15-minute operational load curve.",
    },
    {
        "business_domain": "GENERATION",
        "period_type_code": "DAILY",
        "authoritative_source_code": "PUCSL",
        "secondary_source_code": "CEB",
        "precedence_rank": 1,
        "rationale": "PUCSL daily station bulletins provide audited plant-by-plant daily MWh output.",
    },
    {
        "business_domain": "GENERATION",
        "period_type_code": "MONTHLY",
        "authoritative_source_code": "CEB",
        "secondary_source_code": "PUCSL",
        "precedence_rank": 1,
        "rationale": "CEB Corporate Planning monthly digests provide reconciled utility totals including NCRE billing.",
    },
    {
        "business_domain": "GENERATION",
        "period_type_code": "ANNUAL",
        "authoritative_source_code": "CEB",
        "secondary_source_code": "PUCSL",
        "precedence_rank": 1,
        "rationale": "CEB Statistical Digest provides audited annual generation totals.",
    },
    {
        "business_domain": "SALES",
        "period_type_code": "MONTHLY",
        "authoritative_source_code": "CEB",
        "secondary_source_code": "PUCSL",
        "precedence_rank": 1,
        "rationale": "CEB Statistical Digest is authoritative for billed tariff and provincial sales.",
    },
    {
        "business_domain": "SALES",
        "period_type_code": "ANNUAL",
        "authoritative_source_code": "CEB",
        "secondary_source_code": "PUCSL",
        "precedence_rank": 1,
        "rationale": "CEB Statistical Digest is authoritative for annual billed electricity consumption and revenue.",
    },
    {
        "business_domain": "WEATHER",
        "period_type_code": "DAILY",
        "authoritative_source_code": "NASA_POWER",
        "secondary_source_code": None,
        "precedence_rank": 1,
        "rationale": "NASA POWER MERRA-2/CERES daily point dataset is the primary meteorological source.",
    },
]


def _sl_monsoon_season(month: int) -> str:
    """Return Sri Lanka Department of Meteorology seasonal classification for calendar month."""
    if month in (12, 1, 2):
        return "NORTHEAST_MONSOON"
    if month in (3, 4):
        return "FIRST_INTER_MONSOON"
    if month in (5, 6, 7, 8, 9):
        return "SOUTHWEST_MONSOON"
    return "SECOND_INTER_MONSOON"


def build_calendar_dates(start_year: int = 2019, end_year: int = 2026) -> list[dict[str, Any]]:
    """Generate deterministic calendar date dimension rows for [start_year..end_year]."""
    cur_date = date(start_year, 1, 1)
    final_date = date(end_year, 12, 31)
    rows: list[dict[str, Any]] = []
    while cur_date <= final_date:
        iso_year, iso_week, iso_dow = cur_date.isocalendar()
        _ = iso_year
        q_num = ((cur_date.month - 1) // 3) + 1
        rows.append(
            {
                "date_key": cur_date.year * 10000 + cur_date.month * 100 + cur_date.day,
                "calendar_date": cur_date,
                "day_of_month": cur_date.day,
                "day_of_year": cur_date.timetuple().tm_yday,
                "day_of_week_iso": iso_dow,
                "day_name": cur_date.strftime("%A"),
                "is_weekend": iso_dow in (6, 7),
                "week_of_year_iso": iso_week,
                "month_number": cur_date.month,
                "month_name": cur_date.strftime("%B"),
                "year_month": f"{cur_date.year:04d}-{cur_date.month:02d}",
                "quarter_number": q_num,
                "quarter_name": f"Q{q_num}",
                "calendar_year": cur_date.year,
                "sl_monsoon_season": _sl_monsoon_season(cur_date.month),
            }
        )
        cur_date += timedelta(days=1)
    return rows


def build_time_intervals() -> list[dict[str, Any]]:
    """Generate 96 x 15-minute intervals (keys 1..96) and 24 x hourly intervals (keys 1001..1024)."""
    rows: list[dict[str, Any]] = []
    for idx in range(96):
        total_min = idx * 15
        end_min = (total_min + 15) % 1440
        st = time(total_min // 60, total_min % 60, 0)
        et = time(end_min // 60, end_min % 60, 0)
        if time(18, 30) <= st < time(22, 30):
            block = "PEAK"
        elif time(5, 30) <= st < time(18, 30):
            block = "DAY"
        else:
            block = "OFF_PEAK"
        rows.append(
            {
                "interval_key": idx + 1,
                "interval_type": "15MIN",
                "interval_index": idx + 1,
                "start_time": st,
                "end_time": et,
                "duration_minutes": 15,
                "hour_of_day": st.hour,
                "tariff_time_block": block,
            }
        )

    for hr in range(24):
        st = time(hr, 0, 0)
        et = time((hr + 1) % 24, 0, 0)
        if 19 <= hr <= 21:
            block = "PEAK"
        elif 6 <= hr <= 17:
            block = "DAY"
        else:
            block = "OFF_PEAK"
        rows.append(
            {
                "interval_key": 1001 + hr,
                "interval_type": "HOURLY",
                "interval_index": hr + 1,
                "start_time": st,
                "end_time": et,
                "duration_minutes": 60,
                "hour_of_day": hr,
                "tariff_time_block": block,
            }
        )
    return rows


class ReferenceSeeder:
    """Executes strictly idempotent reference and conformed dimension seeding."""

    def seed_all(self, config: DatabaseConfig | None = None) -> dict[str, int]:
        """Populate all reference and conformed dimension tables inside a single transaction."""
        resolved = config or DatabaseConfig.from_env()
        summary: dict[str, int] = {}

        with get_connection(resolved, autocommit=True) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    # 1. ref.unit
                    cur.executemany(
                        """
                        INSERT INTO ref.unit (
                            unit_code, unit_name, unit_symbol, measurement_dimension,
                            is_canonical_warehouse_unit, description
                        ) VALUES (
                            %(unit_code)s, %(unit_name)s, %(unit_symbol)s, %(measurement_dimension)s,
                            %(is_canonical_warehouse_unit)s, %(description)s
                        )
                        ON CONFLICT (unit_code) DO UPDATE SET
                            unit_name = EXCLUDED.unit_name,
                            unit_symbol = EXCLUDED.unit_symbol,
                            measurement_dimension = EXCLUDED.measurement_dimension,
                            is_canonical_warehouse_unit = EXCLUDED.is_canonical_warehouse_unit,
                            description = EXCLUDED.description;
                        """,
                        UNITS,
                    )
                    summary["ref.unit"] = len(UNITS)

                    # 2. ref.unit_conversion
                    cur.executemany(
                        """
                        INSERT INTO ref.unit_conversion (
                            from_unit_code, to_unit_code, multiplier, additive_offset,
                            requires_interval_hours, formula_description
                        ) VALUES (
                            %(from_unit_code)s, %(to_unit_code)s, %(multiplier)s, %(additive_offset)s,
                            %(requires_interval_hours)s, %(formula_description)s
                        )
                        ON CONFLICT (from_unit_code, to_unit_code) DO UPDATE SET
                            multiplier = EXCLUDED.multiplier,
                            additive_offset = EXCLUDED.additive_offset,
                            requires_interval_hours = EXCLUDED.requires_interval_hours,
                            formula_description = EXCLUDED.formula_description;
                        """,
                        UNIT_CONVERSIONS,
                    )
                    summary["ref.unit_conversion"] = len(UNIT_CONVERSIONS)

                    # 3. ref.reporting_period_type
                    cur.executemany(
                        """
                        INSERT INTO ref.reporting_period_type (
                            period_type_code, period_type_name, nominal_minutes,
                            min_days, max_days, is_subdaily, description
                        ) VALUES (
                            %(period_type_code)s, %(period_type_name)s, %(nominal_minutes)s,
                            %(min_days)s, %(max_days)s, %(is_subdaily)s, %(description)s
                        )
                        ON CONFLICT (period_type_code) DO UPDATE SET
                            period_type_name = EXCLUDED.period_type_name,
                            nominal_minutes = EXCLUDED.nominal_minutes,
                            min_days = EXCLUDED.min_days,
                            max_days = EXCLUDED.max_days,
                            is_subdaily = EXCLUDED.is_subdaily,
                            description = EXCLUDED.description;
                        """,
                        REPORTING_PERIOD_TYPES,
                    )
                    summary["ref.reporting_period_type"] = len(REPORTING_PERIOD_TYPES)

                    # 4. raw.source_system & dw.dim_source_system
                    cur.executemany(
                        """
                        INSERT INTO raw.source_system (
                            source_code, source_name, organization_name,
                            official_url, default_timezone, access_method
                        ) VALUES (
                            %(source_code)s, %(source_name)s, %(organization_name)s,
                            %(official_url)s, %(default_timezone)s, %(access_method)s
                        )
                        ON CONFLICT (source_code) DO UPDATE SET
                            source_name = EXCLUDED.source_name,
                            organization_name = EXCLUDED.organization_name,
                            official_url = EXCLUDED.official_url,
                            default_timezone = EXCLUDED.default_timezone,
                            access_method = EXCLUDED.access_method;
                        """,
                        SOURCE_SYSTEMS,
                    )
                    cur.executemany(
                        """
                        INSERT INTO dw.dim_source_system (
                            source_code, source_name, organization_name, source_category,
                            official_portal_url, default_time_zone, typical_granularity
                        ) VALUES (
                            %(source_code)s, %(source_name)s, %(organization_name)s, %(source_category)s,
                            %(official_url)s, %(default_timezone)s, %(typical_granularity)s
                        )
                        ON CONFLICT (source_code) DO UPDATE SET
                            source_name = EXCLUDED.source_name,
                            organization_name = EXCLUDED.organization_name,
                            source_category = EXCLUDED.source_category,
                            official_portal_url = EXCLUDED.official_portal_url,
                            default_time_zone = EXCLUDED.default_time_zone,
                            typical_granularity = EXCLUDED.typical_granularity;
                        """,
                        SOURCE_SYSTEMS,
                    )
                    summary["dw.dim_source_system"] = len(SOURCE_SYSTEMS)

                    # 5. dw.dim_date & dw.dim_interval
                    cal_rows = build_calendar_dates(2019, 2026)
                    cur.executemany(
                        """
                        INSERT INTO dw.dim_date (
                            date_key, calendar_date, day_of_month, day_of_year,
                            day_of_week_iso, day_name, is_weekend, week_of_year_iso,
                            month_number, month_name, year_month, quarter_number,
                            quarter_name, calendar_year, sl_monsoon_season
                        ) VALUES (
                            %(date_key)s, %(calendar_date)s, %(day_of_month)s, %(day_of_year)s,
                            %(day_of_week_iso)s, %(day_name)s, %(is_weekend)s, %(week_of_year_iso)s,
                            %(month_number)s, %(month_name)s, %(year_month)s, %(quarter_number)s,
                            %(quarter_name)s, %(calendar_year)s, %(sl_monsoon_season)s
                        )
                        ON CONFLICT (date_key) DO UPDATE SET
                            sl_monsoon_season = EXCLUDED.sl_monsoon_season;
                        """,
                        cal_rows,
                    )
                    summary["dw.dim_date"] = len(cal_rows)

                    interval_rows = build_time_intervals()
                    cur.executemany(
                        """
                        INSERT INTO dw.dim_interval (
                            interval_key, interval_type, interval_index, start_time,
                            end_time, duration_minutes, hour_of_day, tariff_time_block
                        ) VALUES (
                            %(interval_key)s, %(interval_type)s, %(interval_index)s, %(start_time)s,
                            %(end_time)s, %(duration_minutes)s, %(hour_of_day)s, %(tariff_time_block)s
                        )
                        ON CONFLICT (interval_key) DO UPDATE SET
                            tariff_time_block = EXCLUDED.tariff_time_block;
                        """,
                        interval_rows,
                    )
                    summary["dw.dim_interval"] = len(interval_rows)

                    # 6. dw.dim_energy_source
                    cur.executemany(
                        """
                        INSERT INTO dw.dim_energy_source (
                            energy_source_code, energy_category, fuel_type,
                            reporting_classification, is_renewable, is_dispatchable, is_indigenous
                        ) VALUES (
                            %(energy_source_code)s, %(energy_category)s, %(fuel_type)s,
                            %(reporting_classification)s, %(is_renewable)s, %(is_dispatchable)s, %(is_indigenous)s
                        )
                        ON CONFLICT (energy_source_code) DO UPDATE SET
                            energy_category = EXCLUDED.energy_category,
                            fuel_type = EXCLUDED.fuel_type,
                            reporting_classification = EXCLUDED.reporting_classification,
                            is_renewable = EXCLUDED.is_renewable,
                            is_dispatchable = EXCLUDED.is_dispatchable,
                            is_indigenous = EXCLUDED.is_indigenous;
                        """,
                        ENERGY_SOURCES,
                    )
                    summary["dw.dim_energy_source"] = len(ENERGY_SOURCES)

                    # 7. dw.dim_region (National first, then child regions)
                    for reg in REGIONS:
                        cur.execute(
                            """
                            INSERT INTO dw.dim_region (
                                region_code, region_name, region_level, iso_code,
                                parent_region_key, source_standard
                            ) VALUES (
                                %s, %s, %s, %s,
                                (SELECT region_key FROM dw.dim_region WHERE region_code = %s),
                                %s
                            )
                            ON CONFLICT (region_code) DO UPDATE SET
                                region_name = EXCLUDED.region_name,
                                region_level = EXCLUDED.region_level,
                                iso_code = EXCLUDED.iso_code,
                                parent_region_key = EXCLUDED.parent_region_key,
                                source_standard = EXCLUDED.source_standard;
                            """,
                            (
                                reg["region_code"],
                                reg["region_name"],
                                reg["region_level"],
                                reg["iso_code"],
                                reg["parent_code"],
                                reg["source_standard"],
                            ),
                        )
                    summary["dw.dim_region"] = len(REGIONS)

                    # 8. dw.dim_consumption_sector
                    cur.executemany(
                        """
                        INSERT INTO dw.dim_consumption_sector (
                            sector_code, sector_name, tariff_group,
                            is_aggregate_bucket, source_classification
                        ) VALUES (
                            %(sector_code)s, %(sector_name)s, %(tariff_group)s,
                            %(is_aggregate_bucket)s, %(source_classification)s
                        )
                        ON CONFLICT (sector_code) DO UPDATE SET
                            sector_name = EXCLUDED.sector_name,
                            tariff_group = EXCLUDED.tariff_group,
                            is_aggregate_bucket = EXCLUDED.is_aggregate_bucket,
                            source_classification = EXCLUDED.source_classification;
                        """,
                        CONSUMPTION_SECTORS,
                    )
                    summary["dw.dim_consumption_sector"] = len(CONSUMPTION_SECTORS)

                    # 9. dw.dim_power_plant
                    for p in POWER_PLANTS:
                        cur.execute(
                            """
                            INSERT INTO dw.dim_power_plant (
                                plant_code, plant_name, entity_level, operator_type,
                                energy_source_key, region_key, hydro_complex,
                                verification_status, effective_from, is_current
                            ) VALUES (
                                %s, %s, %s, %s,
                                (SELECT energy_source_key FROM dw.dim_energy_source WHERE energy_source_code = %s),
                                (SELECT region_key FROM dw.dim_region WHERE region_code = %s),
                                %s, %s, DATE '2000-01-01', TRUE
                            )
                            ON CONFLICT (plant_code, effective_from) DO UPDATE SET
                                plant_name = EXCLUDED.plant_name,
                                entity_level = EXCLUDED.entity_level,
                                operator_type = EXCLUDED.operator_type,
                                energy_source_key = EXCLUDED.energy_source_key,
                                region_key = EXCLUDED.region_key,
                                hydro_complex = EXCLUDED.hydro_complex,
                                verification_status = EXCLUDED.verification_status;
                            """,
                            (
                                p["plant_code"],
                                p["plant_name"],
                                p["entity_level"],
                                p["operator_type"],
                                p["energy_source_code"],
                                p["region_code"],
                                p["hydro_complex"],
                                p["verification_status"],
                            ),
                        )
                    summary["dw.dim_power_plant"] = len(POWER_PLANTS)

                    # 10. dw.dim_weather_location
                    for w in WEATHER_LOCATIONS:
                        cur.execute(
                            """
                            INSERT INTO dw.dim_weather_location (
                                location_code, location_name, energy_zone_type,
                                region_key, latitude_deg, longitude_deg, elevation_m
                            ) VALUES (
                                %s, %s, %s,
                                (SELECT region_key FROM dw.dim_region WHERE region_code = %s),
                                %s, %s, %s
                            )
                            ON CONFLICT (location_code) DO UPDATE SET
                                location_name = EXCLUDED.location_name,
                                energy_zone_type = EXCLUDED.energy_zone_type,
                                region_key = EXCLUDED.region_key,
                                latitude_deg = EXCLUDED.latitude_deg,
                                longitude_deg = EXCLUDED.longitude_deg,
                                elevation_m = EXCLUDED.elevation_m;
                            """,
                            (
                                w["location_code"],
                                w["location_name"],
                                w["energy_zone_type"],
                                w["region_code"],
                                w["latitude_deg"],
                                w["longitude_deg"],
                                w["elevation_m"],
                            ),
                        )
                    summary["dw.dim_weather_location"] = len(WEATHER_LOCATIONS)

                    # 11. dw.dim_metric
                    cur.executemany(
                        """
                        INSERT INTO dw.dim_metric (
                            metric_code, metric_name, business_domain, measurement_class,
                            canonical_unit_code, generation_boundary, value_nature,
                            aggregation_behavior, is_summable_across_time,
                            is_summable_across_entities, comparability_group, definition_notes
                        ) VALUES (
                            %(metric_code)s, %(metric_name)s, %(business_domain)s, %(measurement_class)s,
                            %(canonical_unit_code)s, %(generation_boundary)s, %(value_nature)s,
                            %(aggregation_behavior)s, %(is_summable_across_time)s,
                            %(is_summable_across_entities)s, %(comparability_group)s, %(definition_notes)s
                        )
                        ON CONFLICT (metric_code) DO UPDATE SET
                            metric_name = EXCLUDED.metric_name,
                            business_domain = EXCLUDED.business_domain,
                            measurement_class = EXCLUDED.measurement_class,
                            canonical_unit_code = EXCLUDED.canonical_unit_code,
                            generation_boundary = EXCLUDED.generation_boundary,
                            value_nature = EXCLUDED.value_nature,
                            aggregation_behavior = EXCLUDED.aggregation_behavior,
                            is_summable_across_time = EXCLUDED.is_summable_across_time,
                            is_summable_across_entities = EXCLUDED.is_summable_across_entities,
                            comparability_group = EXCLUDED.comparability_group,
                            definition_notes = EXCLUDED.definition_notes;
                        """,
                        METRICS,
                    )
                    summary["dw.dim_metric"] = len(METRICS)

                    # 12. ref.* mappings, DQ rules & precedence
                    cur.executemany(
                        """
                        INSERT INTO ref.plant_alias (
                            source_code, alias_name, canonical_plant_code,
                            effective_from, verification_status, verification_evidence, verified_by
                        ) VALUES (
                            %(source_code)s, %(alias_name)s, %(canonical_plant_code)s,
                            DATE '2000-01-01', %(verification_status)s, %(verification_evidence)s, %(verified_by)s
                        )
                        ON CONFLICT (source_code, alias_name, effective_from) DO UPDATE SET
                            canonical_plant_code = EXCLUDED.canonical_plant_code,
                            verification_status = EXCLUDED.verification_status,
                            verification_evidence = EXCLUDED.verification_evidence,
                            verified_by = EXCLUDED.verified_by;
                        """,
                        PLANT_ALIASES,
                    )
                    cur.executemany(
                        """
                        INSERT INTO ref.energy_source_mapping (
                            source_code, raw_source_label, canonical_energy_source_code,
                            effective_from, verification_status, verification_evidence
                        ) VALUES (
                            %(source_code)s, %(raw_source_label)s, %(canonical_energy_source_code)s,
                            DATE '2000-01-01', %(verification_status)s, %(verification_evidence)s
                        )
                        ON CONFLICT (source_code, raw_source_label, effective_from) DO UPDATE SET
                            canonical_energy_source_code = EXCLUDED.canonical_energy_source_code,
                            verification_status = EXCLUDED.verification_status,
                            verification_evidence = EXCLUDED.verification_evidence;
                        """,
                        ENERGY_SOURCE_MAPPINGS,
                    )
                    cur.executemany(
                        """
                        INSERT INTO ref.region_alias (
                            source_code, alias_name, canonical_region_code,
                            verification_status, verification_evidence
                        ) VALUES (
                            %(source_code)s, %(alias_name)s, %(canonical_region_code)s,
                            %(verification_status)s, %(verification_evidence)s
                        )
                        ON CONFLICT (source_code, alias_name) DO UPDATE SET
                            canonical_region_code = EXCLUDED.canonical_region_code,
                            verification_status = EXCLUDED.verification_status,
                            verification_evidence = EXCLUDED.verification_evidence;
                        """,
                        REGION_ALIASES,
                    )
                    cur.executemany(
                        """
                        INSERT INTO ref.metric_mapping (
                            source_code, source_field_name, canonical_metric_code,
                            source_unit_code, verification_status, notes
                        ) VALUES (
                            %(source_code)s, %(source_field_name)s, %(canonical_metric_code)s,
                            %(source_unit_code)s, %(verification_status)s, %(notes)s
                        )
                        ON CONFLICT (source_code, source_field_name) DO UPDATE SET
                            canonical_metric_code = EXCLUDED.canonical_metric_code,
                            source_unit_code = EXCLUDED.source_unit_code,
                            verification_status = EXCLUDED.verification_status,
                            notes = EXCLUDED.notes;
                        """,
                        METRIC_MAPPINGS,
                    )
                    cur.executemany(
                        """
                        INSERT INTO ref.data_quality_rule (
                            rule_code, rule_name, issue_classification, target_domain,
                            default_severity, blocks_warehouse_load, rule_expression_summary
                        ) VALUES (
                            %(rule_code)s, %(rule_name)s, %(issue_classification)s, %(target_domain)s,
                            %(default_severity)s, %(blocks_warehouse_load)s, %(rule_expression_summary)s
                        )
                        ON CONFLICT (rule_code) DO UPDATE SET
                            rule_name = EXCLUDED.rule_name,
                            issue_classification = EXCLUDED.issue_classification,
                            target_domain = EXCLUDED.target_domain,
                            default_severity = EXCLUDED.default_severity,
                            blocks_warehouse_load = EXCLUDED.blocks_warehouse_load,
                            rule_expression_summary = EXCLUDED.rule_expression_summary;
                        """,
                        DATA_QUALITY_RULES,
                    )
                    cur.executemany(
                        """
                        INSERT INTO ref.source_precedence (
                            business_domain, period_type_code, authoritative_source_code,
                            secondary_source_code, precedence_rank, rationale
                        ) VALUES (
                            %(business_domain)s, %(period_type_code)s, %(authoritative_source_code)s,
                            %(secondary_source_code)s, %(precedence_rank)s, %(rationale)s
                        )
                        ON CONFLICT (business_domain, period_type_code, authoritative_source_code) DO UPDATE SET
                            secondary_source_code = EXCLUDED.secondary_source_code,
                            precedence_rank = EXCLUDED.precedence_rank,
                            rationale = EXCLUDED.rationale;
                        """,
                        SOURCE_PRECEDENCE,
                    )
                    summary["ref.data_quality_rule"] = len(DATA_QUALITY_RULES)

        return summary


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for idempotent reference seeding."""
    parser = argparse.ArgumentParser(description="Seed verified reference and dimension tables.")
    parser.add_argument(
        "--test-db",
        action="store_true",
        help="Seed POSTGRES_TEST_DB instead of primary POSTGRES_DB",
    )
    args = parser.parse_args(argv)
    cfg = DatabaseConfig.from_env(use_test_db=args.test_db)
    seeder = ReferenceSeeder()
    counts = seeder.seed_all(cfg)
    print(f"Reference seeding completed idempotently on '{cfg.dbname}':")
    for tbl, cnt in counts.items():
        print(f"  - {tbl}: {cnt} rows ensured")
    print(
        "  - Production fact tables (dw.fact_*): 0 rows seeded (pending Phase 2 real data ingestion)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
