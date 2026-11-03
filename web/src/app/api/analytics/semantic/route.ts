import { NextRequest, NextResponse } from "next/server";
import {
  SEMANTIC_MEASURES,
  SEMANTIC_DIMENSIONS,
  validateMeasureDimensionGrain,
} from "@/lib/analytics/semantic-layer";
import { getAnalyticsData } from "@/lib/db/snapshot-loader";
import { toNumeric } from "@/lib/formatting/units";

export async function GET() {
  return NextResponse.json({
    success: true,
    measures: Object.values(SEMANTIC_MEASURES),
    dimensions: Object.values(SEMANTIC_DIMENSIONS),
    governance: {
      factGrainEnforced: true,
      arbitrarySqlProhibited: true,
      safeAggregationOnly: true,
    },
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { measureId, dimensionId, filterValue } = body;

    if (!measureId || !dimensionId) {
      return NextResponse.json(
        {
          success: false,
          error: "Both 'measureId' and 'dimensionId' are required.",
        },
        { status: 400 }
      );
    }

    // 1. Fact Grain Compatibility Check
    const grainCheck = validateMeasureDimensionGrain(measureId, dimensionId);
    if (!grainCheck.compatible) {
      return NextResponse.json(
        {
          success: false,
          error: `Grain incompatibility: ${grainCheck.reason}`,
        },
        { status: 422 }
      );
    }

    const measure = SEMANTIC_MEASURES[measureId];
    const dimension = SEMANTIC_DIMENSIONS[dimensionId];

    // 2. Map semantic request to safe underlying query
    let baseQueryId = "Q01";
    let groupByKey = "energy_category";
    let valKey = "total_energy_mwh";

    if (measureId === "generation_mwh") {
      baseQueryId = "Q01";
      groupByKey = dimensionId === "power_plant" ? "plant_name" : "energy_category";
      valKey = "total_energy_mwh";
    } else if (measureId === "energy_sold_mwh") {
      baseQueryId = "Q09";
      groupByKey = dimensionId === "calendar_year" ? "calendar_year" : "tariff_sector";
      valKey = "energy_sold_mwh";
    } else if (measureId === "active_power_mw") {
      baseQueryId = "Q05";
      groupByKey = "interval_index";
      valKey = "weekday_mean_mw";
    } else if (measureId === "solar_irradiance_sw_dwn" || measureId === "air_temp_2m_c") {
      baseQueryId = "Q13";
      groupByKey = "month_name";
      valKey = "avg_peak_sun_hours_psh";
    }

    const queryRes = await getAnalyticsData(baseQueryId);
    if (!queryRes.success) {
      return NextResponse.json(
        {
          success: false,
          error: `Underlying analytical execution failed for ${baseQueryId}.`,
        },
        { status: 500 }
      );
    }

    // Aggregate safely in memory over verified grain
    const aggMap = new Map<string, number>();
    queryRes.data.forEach((row) => {
      const dimVal = String(row[groupByKey] || row[dimensionId] || "Other");
      const rawVal = row[valKey] !== undefined ? row[valKey] : row[measureId];
      const numVal = toNumeric(rawVal as string | number | null | undefined) || 0;
      if (filterValue && filterValue !== "all" && !dimVal.toLowerCase().includes(filterValue.toLowerCase())) {
        return;
      }
      aggMap.set(dimVal, (aggMap.get(dimVal) || 0) + numVal);
    });

    const aggregated = Array.from(aggMap.entries()).map(([dim, val]) => ({
      dimension: dim,
      measure: Number(val.toFixed(2)),
      unit: measure.unit,
    }));

    return NextResponse.json({
      success: true,
      measure: measure.name,
      dimension: dimension.name,
      unit: measure.unit,
      sourceQuery: baseQueryId,
      sourceMode: queryRes.sourceMode,
      results: aggregated,
    });
  } catch (err) {
    return NextResponse.json(
      {
        success: false,
        error: (err as Error).message,
      },
      { status: 500 }
    );
  }
}
