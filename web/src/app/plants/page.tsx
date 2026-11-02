"use client";

import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { formatMW, formatPercent, toNumeric } from "@/lib/formatting/units";

interface PlantNameplateRecord {
  station_name: string;
  technology_type: string;
  operator_type: string;
  installed_capacity_mw: number | string;
  observed_peak_mw: number | string;
  peak_to_nameplate_ratio_pct: number | string;
  mean_power_mw: number | string;
  mean_capacity_utilization_pct: number | string;
  peak_headroom_mw: number | string;
  operational_delivery_status: string;
  peak_ratio_rank: number;
  [key: string]: unknown;
}

export default function PlantsPage() {
  const [nameplateData, setNameplateData] = useState<PlantNameplateRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/analytics/Q18")
      .then((res) => res.json())
      .then((res) => {
        if (res.success) setNameplateData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load Q18 plant analytics:", err);
        setLoading(false);
      });
  }, []);

  const columns: ColumnDef<PlantNameplateRecord>[] = [
    {
      key: "peak_ratio_rank",
      header: "RANK",
      sortable: true,
      className: "font-bold text-[#19222D]",
    },
    {
      key: "station_name",
      header: "POWER STATION",
      sortable: true,
      className: "font-semibold text-[#19222D]",
    },
    {
      key: "technology_type",
      header: "TYPE",
      sortable: true,
    },
    {
      key: "operator_type",
      header: "OPERATOR",
      sortable: true,
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
      key: "peak_to_nameplate_ratio_pct",
      header: "PEAK/NAMEPLATE",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const val = toNumeric(r.peak_to_nameplate_ratio_pct);
        if (val === null) return "—";
        const isOver = val > 100;
        return (
          <span
            className={`px-2 py-0.5 rounded-[6px] text-[11px] font-bold ${
              isOver
                ? "bg-[#FDEDEC] text-[#B03A2E]"
                : val >= 85
                ? "bg-[#E8F6F2] text-[#177763]"
                : "bg-[#FFF6E8] text-[#9A6715]"
            }`}
          >
            {val.toFixed(1)}%
          </span>
        );
      },
    },
    {
      key: "mean_capacity_utilization_pct",
      header: "UTILIZATION",
      sortable: true,
      align: "right",
      accessor: (r) => formatPercent(r.mean_capacity_utilization_pct, 1),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Member 5 / Plant Performance & Operational Outages"
        title="Plant Performance & Operational Outages"
        titleAccent="."
        description="Generating station availability, zero-dispatch outage duty cycles, peak dispatch vs reference nameplate ratios, and thermal peaker evening order during March 2024."
        onExportCsv={() => window.open("/api/exports/Q18", "_blank")}
      />

      {/* KPI row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="Lakvijaya 3-Unit Availability"
          value="100.00"
          unit="%"
          period="2,976 Intervals Online"
          sourcePill="Q19"
          accentColor="#229C88"
        />
        <KpiCard
          name="West Coast Peak Dispatch"
          value="289.00"
          unit="MW"
          period="107% of 270 MW Nameplate"
          sourcePill="Q18"
          accentColor="#19222D"
        />
        <KpiCard
          name="Cold Standby Plants"
          value="2"
          unit="Stations"
          period="Matugama & Ace Matara"
          sourcePill="Q17"
          accentColor="#E9A43B"
        />
        <KpiCard
          name="Victoria Peak Hydro"
          value="197.00"
          unit="MW"
          period="93.8% of 210 MW Nameplate"
          sourcePill="Q18"
          accentColor="#4278B9"
        />
      </section>

      {/* Visual Chart: Peak vs Installed Nameplate */}
      <SimpleBarChart
        title="Observed Peak Dispatch vs Reference Nameplate Ratio"
        subtitle="Identifies operating headroom and potential thermal or hydro peaking over-commitments"
        badge="PUCSL Telemetry · Q18"
        unit="%"
        data={nameplateData.slice(0, 8).map((d) => {
          const ratio = toNumeric(d.peak_to_nameplate_ratio_pct) || 0;
          const peak = toNumeric(d.observed_peak_mw) || 0;
          const nameplate = toNumeric(d.installed_capacity_mw) || 0;
          return {
            label: d.station_name,
            value: ratio,
            formattedValue: `${ratio.toFixed(1)}% (${peak.toFixed(0)} MW / ${nameplate.toFixed(0)} MW)`,
            sublabel: d.technology_type,
            color:
              ratio > 100
                ? "#D65F62"
                : ratio >= 90
                ? "#4278B9"
                : "#E9A43B",
          };
        })}
      />

      {/* Plant Nameplate Utilization Table */}
      {loading ? (
        <div className="py-12 text-center text-[#9AA5B0]">Loading power plant telemetry...</div>
      ) : (
        <DataTable
          title="Plant Nameplate Capacity & Peak Observed Dispatch Audit"
          subtitle="Comparison of observed maximum 15-minute dispatch against CEB reference installed nameplate"
          badge="SQL Query Q18"
          data={nameplateData}
          columns={columns}
          filename="gridlens-plant-utilization-Q18.csv"
        />
      )}
    </div>
  );
}
