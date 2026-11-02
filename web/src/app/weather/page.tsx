"use client";

import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { formatNumber, toNumeric } from "@/lib/formatting/units";

interface SolarIrradianceRecord {
  calendar_year: number;
  location_code: string;
  location_name: string;
  valid_days_measured: number | string;
  min_daily_irradiance_mj: number | string;
  mean_daily_irradiance_mj: number | string;
  max_daily_irradiance_mj: number | string;
  stddev_irradiance_mj: number | string;
  mean_daily_kwh_per_m2: number | string;
  approx_peak_sun_hours_psh: number | string;
  [key: string]: unknown;
}

export default function WeatherPage() {
  const [solarData, setSolarData] = useState<SolarIrradianceRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/analytics/Q13")
      .then((res) => res.json())
      .then((res) => {
        if (res.success) setSolarData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load Q13 weather analytics:", err);
        setLoading(false);
      });
  }, []);

  const columns: ColumnDef<SolarIrradianceRecord>[] = [
    {
      key: "calendar_year",
      header: "YEAR",
      sortable: true,
      className: "font-bold text-[#19222D]",
    },
    {
      key: "location_name",
      header: "METEOROLOGICAL STATION",
      sortable: true,
      className: "font-semibold text-[#19222D]",
    },
    {
      key: "valid_days_measured",
      header: "DAYS RECORDED",
      sortable: true,
      align: "right",
      accessor: (r) => `${r.valid_days_measured} days`,
    },
    {
      key: "mean_daily_irradiance_mj",
      header: "MEAN INSOLATION (MJ/M²)",
      sortable: true,
      align: "right",
      accessor: (r) => `${formatNumber(r.mean_daily_irradiance_mj, 2)} MJ/m²`,
    },
    {
      key: "mean_daily_kwh_per_m2",
      header: "SOLAR ENERGY (KWH/M²/DAY)",
      sortable: true,
      align: "right",
      accessor: (r) => `${formatNumber(r.mean_daily_kwh_per_m2, 3)} kWh/m²`,
    },
    {
      key: "approx_peak_sun_hours_psh",
      header: "PEAK SUN HOURS (PSH)",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const val = toNumeric(r.approx_peak_sun_hours_psh);
        return (
          <span className="px-2 py-0.5 rounded-[6px] bg-[#FFF6E8] text-[#9A6715] text-[11px] font-bold">
            {val !== null ? `${val.toFixed(2)} hrs/day` : "—"}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Member 4 / Weather & Renewable Potential"
        title="Weather & Renewable Potential"
        titleAccent="."
        description="NASA POWER satellite meteorology, solar insolation (Peak Sun Hours), temperature-to-demand correlation, and wind resource potential across Sri Lanka (2020–2024)."
        onExportCsv={() => window.open("/api/exports/Q13", "_blank")}
      />

      {/* KPI row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="Mannar Mean PSH"
          value="5.48"
          unit="hrs/day"
          period="Dry Zone Solar"
          sourcePill="NASA"
          accentColor="#E9A43B"
        />
        <KpiCard
          name="Victoria Catchment PSH"
          value="5.35"
          unit="hrs/day"
          period="Central Highlands"
          sourcePill="NASA"
          accentColor="#229C88"
        />
        <KpiCard
          name="Temp vs Daily Energy (r)"
          value="+0.125"
          unit="Pearson r"
          period="Cooling Elasticity"
          sourcePill="Q14"
          accentColor="#4278B9"
        />
        <KpiCard
          name="Meteorological Facts"
          value="21,924"
          unit="Rows"
          period="5-Year Complete History"
          sourcePill="Warehouse"
          accentColor="#19222D"
        />
      </section>

      {/* Solar PSH Comparison Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8">
          <SimpleBarChart
            title="Annual Peak Sun Hours (PSH) by Geographical Corridor"
            subtitle="Calculated from NASA POWER daily solar insolation (ALLSKY_SFC_SW_DWN)"
            badge="NASA POWER · Q13"
            unit="PSH"
            data={solarData.map((d) => {
              const psh = toNumeric(d.approx_peak_sun_hours_psh) || 0;
              const kwh = toNumeric(d.mean_daily_kwh_per_m2) || 0;
              return {
                label: `${d.calendar_year} · ${d.location_code === "LOC_MANNAR_WIND" ? "Mannar Corridor" : "Victoria Basin"}`,
                value: psh,
                formattedValue: `${psh.toFixed(2)} hrs/day`,
                sublabel: `${kwh.toFixed(2)} kWh/m²/day`,
                color: d.location_code === "LOC_MANNAR_WIND" ? "#E9A43B" : "#229C88",
              };
            })}
          />
        </div>

        {/* Temperature Correlation Panel */}
        <div className="lg:col-span-4">
          <div className="card-glass p-6 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-[17px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
                    Temperature vs Demand
                  </h3>
                  <p className="text-[12px] text-[#86919E] mt-1 m-0">
                    March 2024 paired statistical regression
                  </p>
                </div>
                <span className="text-[11px] font-bold text-[#7D8896] px-2.5 py-1 border border-[#E7EBF0] rounded-[7px] bg-[#FAFBFC]">
                  Q14
                </span>
              </div>

              <div className="space-y-4 my-4">
                <div className="p-3.5 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0]">
                  <div className="text-[11px] font-semibold text-[#86919E] uppercase">
                    Daily Energy Correlation
                  </div>
                  <div className="text-[24px] font-extrabold text-[#229C88] tracking-tight">
                    +0.1248
                  </div>
                  <div className="text-[11px] text-[#637185] mt-1">
                    Mild positive link: hotter days stimulate higher daytime air-conditioning and refrigeration cooling loads.
                  </div>
                </div>

                <div className="p-3.5 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0]">
                  <div className="text-[11px] font-semibold text-[#86919E] uppercase">
                    Peak Dispatch Correlation
                  </div>
                  <div className="text-[24px] font-extrabold text-[#19222D] tracking-tight">
                    +0.0083
                  </div>
                  <div className="text-[11px] text-[#637185] mt-1">
                    Near-zero correlation with evening peak (19:00–21:00) as solar radiation and daytime heat dissipate before domestic evening lighting surge.
                  </div>
                </div>
              </div>
            </div>

            <div className="p-3 border border-[#ECF0F4] rounded-[8px] bg-[#FAFBFC] text-[11px] text-[#687686]">
              Verified across 31 paired daily observations in March 2024.
            </div>
          </div>
        </div>
      </div>

      {/* Solar Irradiance Table */}
      {loading ? (
        <div className="py-12 text-center text-[#9AA5B0]">Loading meteorological observations...</div>
      ) : (
        <DataTable
          title="Solar Irradiance & Peak Sun Hours Observations"
          subtitle="NASA POWER surface downward solar irradiance measurements across 5 historical years"
          badge="SQL Query Q13"
          data={solarData}
          columns={columns}
          filename="gridlens-solar-irradiance-Q13.csv"
        />
      )}
    </div>
  );
}
