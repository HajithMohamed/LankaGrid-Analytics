/**
 * Controlled Semantic Layer for GridLens Analytics.
 * Enforces fact-grain compatibility, prevents double counting, and maps approved
 * analytical measures and dimensions without allowing arbitrary SQL injection.
 */

export interface SemanticMeasure {
  id: string;
  name: string;
  unit: string;
  description: string;
  compatibleFacts: string[];
  defaultAggregation: "SUM" | "AVG" | "MAX" | "MIN" | "COUNT";
  supportedAggregations: Array<"SUM" | "AVG" | "MAX" | "MIN" | "COUNT">;
  queryReference: string;
}

export interface SemanticDimension {
  id: string;
  name: string;
  dimensionTable: string;
  hierarchies?: string[];
  allowedValues?: string[];
}

export interface SemanticCubeDefinition {
  id: string;
  name: string;
  description: string;
  grain: string;
  allowedMeasures: string[];
  allowedDimensions: string[];
  baseQueryId: string;
}

export const SEMANTIC_MEASURES: Record<string, SemanticMeasure> = {
  generation_mwh: {
    id: "generation_mwh",
    name: "Electricity Generated",
    unit: "MWh",
    description: "Integrated electrical energy output over time.",
    compatibleFacts: ["fact_dispatch_interval", "fact_generation_period"],
    defaultAggregation: "SUM",
    supportedAggregations: ["SUM", "AVG", "MAX"],
    queryReference: "Q01, Q03, Q04, Q19",
  },
  active_power_mw: {
    id: "active_power_mw",
    name: "Active Power Demand Rate",
    unit: "MW",
    description: "Instantaneous dispatch rate measured in 15-minute intervals.",
    compatibleFacts: ["fact_dispatch_interval"],
    defaultAggregation: "AVG",
    supportedAggregations: ["AVG", "MAX", "MIN"],
    queryReference: "Q05, Q06, Q07",
  },
  energy_sold_mwh: {
    id: "energy_sold_mwh",
    name: "Audited Billed Sales",
    unit: "MWh",
    description: "Final statutory consumer billing energy from CEB statistical digests.",
    compatibleFacts: ["fact_electricity_sales"],
    defaultAggregation: "SUM",
    supportedAggregations: ["SUM", "AVG"],
    queryReference: "Q09, Q10, Q21",
  },
  solar_irradiance_sw_dwn: {
    id: "solar_irradiance_sw_dwn",
    name: "Solar Irradiance (All-Sky)",
    unit: "MJ/m²/day",
    description: "Surface shortwave downward solar radiation from NASA POWER.",
    compatibleFacts: ["fact_weather_daily"],
    defaultAggregation: "AVG",
    supportedAggregations: ["AVG", "MAX"],
    queryReference: "Q13",
  },
  air_temp_2m_c: {
    id: "air_temp_2m_c",
    name: "Air Temperature (2m)",
    unit: "°C",
    description: "Ambient dry bulb air temperature at 2-meter elevation.",
    compatibleFacts: ["fact_weather_daily"],
    defaultAggregation: "AVG",
    supportedAggregations: ["AVG", "MAX", "MIN"],
    queryReference: "Q14",
  },
  wind_speed_50m_ms: {
    id: "wind_speed_50m_ms",
    name: "Wind Speed (50m Hub Height)",
    unit: "m/s",
    description: "Wind velocity measured at 50-meter hub altitude.",
    compatibleFacts: ["fact_weather_daily"],
    defaultAggregation: "AVG",
    supportedAggregations: ["AVG", "MAX"],
    queryReference: "Q16",
  },
  quarantine_issues_count: {
    id: "quarantine_issues_count",
    name: "Quarantined Data Quality Issues",
    unit: "Records",
    description: "Number of isolated records violating automated warehouse quality gates.",
    compatibleFacts: ["data_quality_issue"],
    defaultAggregation: "COUNT",
    supportedAggregations: ["COUNT"],
    queryReference: "Q23",
  },
};

export const SEMANTIC_DIMENSIONS: Record<string, SemanticDimension> = {
  energy_category: {
    id: "energy_category",
    name: "Energy Category",
    dimensionTable: "dim_energy_source",
    allowedValues: ["Thermal Coal", "Thermal Oil", "Major Hydro", "Solar", "Wind", "Biomass"],
  },
  power_plant: {
    id: "power_plant",
    name: "Generating Station",
    dimensionTable: "dim_power_plant",
  },
  calendar_year: {
    id: "calendar_year",
    name: "Calendar Year",
    dimensionTable: "dim_date",
    allowedValues: ["2020", "2021", "2022", "2023", "2024"],
  },
  tariff_time_block: {
    id: "tariff_time_block",
    name: "Time-of-Use Regime",
    dimensionTable: "dim_interval",
    allowedValues: ["DAY", "PEAK", "OFF-PEAK"],
  },
  consumption_sector: {
    id: "consumption_sector",
    name: "Consumption Sector",
    dimensionTable: "dim_consumption_sector",
    allowedValues: ["Domestic", "Industrial", "General Purpose", "Hotel", "Street Lighting", "LECO Bulk"],
  },
  weather_location: {
    id: "weather_location",
    name: "Weather Station",
    dimensionTable: "dim_weather_location",
    allowedValues: ["Victoria Dam Catchment", "Mannar Wind Corridor"],
  },
};

/**
 * Validate whether a requested measure and dimension share a compatible fact grain.
 * Prevents invalid aggregations (e.g. cross-multiplying 15-minute dispatch with annual billing).
 */
export function validateMeasureDimensionGrain(
  measureId: string,
  dimensionId: string
): { compatible: boolean; reason?: string } {
  const measure = SEMANTIC_MEASURES[measureId];
  const dimension = SEMANTIC_DIMENSIONS[dimensionId];

  if (!measure) return { compatible: false, reason: `Unknown measure: ${measureId}` };
  if (!dimension) return { compatible: false, reason: `Unknown dimension: ${dimensionId}` };

  // Grain rules
  if (measureId === "energy_sold_mwh" && dimensionId === "tariff_time_block") {
    return {
      compatible: false,
      reason: "CEB audited sales data is published at annual granularity, not 15-minute TOU interval grain.",
    };
  }

  if (
    (measureId === "solar_irradiance_sw_dwn" || measureId === "wind_speed_50m_ms") &&
    dimensionId === "power_plant"
  ) {
    return {
      compatible: false,
      reason: "NASA POWER observations are linked to meteorological coordinates (Victoria, Mannar), not plant IDs.",
    };
  }

  return { compatible: true };
}
