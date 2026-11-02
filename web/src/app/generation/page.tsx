"use client";

import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { GenerationDonutChart } from "@/components/charts/generation-donut-chart";
import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { formatMW, formatMWh, formatPercent, toNumeric } from "@/lib/formatting/units";

interface PlantCapacityRecord {
  plant_name: string;
  energy_category: string;
  operator_category: string;
  installed_capacity_mw: number | string;
  observed_peak_mw: number | string;
  total_generation_mwh: number | string;
  duty_cycle_pct: number | string;
  official_capacity_factor_pct: number | string;
  generation_rank: number;
  [key: string]: unknown;
}

export default function GenerationPage() {
  const [plantRecords, setPlantRecords] = useState<PlantCapacityRecord[]>([]);
  const [filterSource, setFilterSource] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/analytics/Q03")
      .then((res) => res.json())
      .then((res) => {
        if (res.success) setPlantRecords(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch Q03 capacity factors:", err);
        setLoading(false);
      });
  }, []);

  const filteredPlants =
    filterSource === "all"
      ? plantRecords
      : plantRecords.filter((p) =>
          String(p.energy_category || "").toLowerCase().includes(filterSource.toLowerCase())
        );

  const columns: ColumnDef<PlantCapacityRecord>[] = [
    {
      key: "generation_rank",
      header: "RANK",
      sortable: true,
      className: "font-bold text-[#19222D]",
    },
    {
      key: "plant_name",
      header: "POWER PLANT",
      sortable: true,
      className: "font-semibold text-[#19222D]",
    },
    {
      key: "energy_category",
      header: "FUEL CATEGORY",
      sortable: true,
      accessor: (r) => (
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
            r.energy_category === "Thermal Coal"
              ? "bg-[#EAECEE] text-[#343D49]"
              : r.energy_category === "Thermal Oil"
              ? "bg-[#FFF6E8] text-[#9A6715]"
              : "bg-[#EAF2FA] text-[#205796]"
          }`}
        >
          {String(r.energy_category)}
        </span>
      ),
    },
    {
      key: "installed_capacity_mw",
      header: "NAMEPLATE (MW)",
      sortable: true,
      align: "right",
      accessor: (r) => formatMW(r.installed_capacity_mw, 1),
    },
    {
      key: "observed_peak_mw",
      header: "PEAK DISPATCH (MW)",
      sortable: true,
      align: "right",
      accessor: (r) => formatMW(r.observed_peak_mw, 1),
    },
    {
      key: "total_generation_mwh",
      header: "ENERGY GENERATED (MWH)",
      sortable: true,
      align: "right",
      accessor: (r) => formatMWh(r.total_generation_mwh, 1),
    },
    {
      key: "duty_cycle_pct",
      header: "DUTY CYCLE",
      sortable: true,
      align: "right",
      accessor: (r) => formatPercent(r.duty_cycle_pct, 1),
    },
    {
      key: "official_capacity_factor_pct",
      header: "CAPACITY FACTOR",
      sortable: true,
      align: "right",
      accessor: (r) => (
        <span className="px-2 py-0.5 rounded-[6px] bg-[#E8F6F2] text-[#177763] text-[11px] font-bold">
          {formatPercent(r.official_capacity_factor_pct, 1)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Member 1 / Generation & Renewables"
        title="Generation Mix & Renewables"
        titleAccent="."
        description="Detailed generation technology breakdown, plant capacity factors, and renewable energy shares during March 2024 (PUCSL operational dispatch)."
        onExportCsv={() => window.open("/api/exports/Q01", "_blank")}
      >
        <div className="flex items-center gap-2">
          <label className="text-[12px] font-semibold text-[#748091]">Filter Fuel:</label>
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="h-[41px] px-3 rounded-[10px] bg-white border border-[#E2E7EE] text-[#19222D] font-bold text-[12px] outline-none"
          >
            <option value="all">All Categories</option>
            <option value="coal">Thermal Coal</option>
            <option value="oil">Thermal Oil</option>
            <option value="hydro">Hydro</option>
          </select>
        </div>
      </PageHeader>

      {/* KPI row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="March Total Generation"
          value="1,399,337.00"
          unit="MWh"
          period="March 2024"
          sourcePill="PUCSL"
          accentColor="#19222D"
        />
        <KpiCard
          name="Lakvijaya Coal Total"
          value="595,524.50"
          unit="MWh"
          period="42.56% Share"
          sourcePill="Q01"
          accentColor="#343D49"
        />
        <KpiCard
          name="Thermal Oil Generation"
          value="387,450.75"
          unit="MWh"
          period="27.69% Share"
          sourcePill="Q01"
          accentColor="#E9A43B"
        />
        <KpiCard
          name="Total Hydro (Major + Mini)"
          value="361,909.25"
          unit="MWh"
          period="25.86% Share"
          sourcePill="Q01"
          accentColor="#4278B9"
        />
      </section>

      {/* Visual Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-5">
          <GenerationDonutChart />
        </div>
        <div className="lg:col-span-7">
          <SimpleBarChart
            title="Plant Capacity Factor Comparison"
            subtitle="Actual generation vs theoretical maximum at rated nameplate (March 2024, 744 hrs)"
            badge="PUCSL · Q03"
            unit="%"
            data={plantRecords.slice(0, 7).map((p) => {
              const cf = toNumeric(p.official_capacity_factor_pct) || 0;
              return {
                label: p.plant_name,
                value: cf,
                formattedValue: `${cf.toFixed(1)}%`,
                sublabel: String(p.energy_category),
                color:
                  p.energy_category === "Thermal Coal"
                    ? "#343D49"
                    : p.energy_category === "Thermal Oil"
                    ? "#E9A43B"
                    : "#4278B9",
              };
            })}
          />
        </div>
      </div>

      {/* Plant Capacity Factor Table */}
      {loading ? (
        <div className="py-12 text-center text-[#9AA5B0]">Loading capacity factor metrics...</div>
      ) : (
        <DataTable
          title="Plant Capacity Factor & Utilization Ranking"
          subtitle="Ranked by total energy generation during March 2024 (PUCSL telemetry)"
          badge="SQL Query Q03"
          data={filteredPlants}
          columns={columns}
          filename="gridlens-plant-capacity-factors-Q03.csv"
        />
      )}
    </div>
  );
}
