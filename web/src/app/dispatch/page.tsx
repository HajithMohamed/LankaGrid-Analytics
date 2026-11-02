"use client";

import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { DiurnalLoadCurveChart, DiurnalPoint } from "@/components/charts/diurnal-load-curve-chart";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { formatMW, toNumeric } from "@/lib/formatting/units";

interface BaseloadVolatilityRecord {
  plant_name: string;
  energy_category: string;
  fuel_type: string;
  min_dispatched_mw: number | string;
  peak_dispatched_mw: number | string;
  mean_dispatched_mw: number | string;
  stddev_dispatched_mw: number | string;
  coefficient_of_variation: number | string;
  operational_load_factor_pct: number | string;
  operational_behavior_class: string;
  baseload_stability_rank: number;
  [key: string]: unknown;
}

export default function DispatchPage() {
  const [diurnalData, setDiurnalData] = useState<DiurnalPoint[]>([]);
  const [volatilityData, setVolatilityData] = useState<BaseloadVolatilityRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/Q05").then((res) => res.json()),
      fetch("/api/analytics/Q07").then((res) => res.json()),
    ])
      .then(([q05Res, q07Res]) => {
        if (q05Res.success) setDiurnalData(q05Res.data);
        if (q07Res.success) setVolatilityData(q07Res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch dispatch analytics:", err);
        setLoading(false);
      });
  }, []);

  const columns: ColumnDef<BaseloadVolatilityRecord>[] = [
    {
      key: "baseload_stability_rank",
      header: "RANK",
      sortable: true,
      className: "font-bold text-[#19222D]",
    },
    {
      key: "plant_name",
      header: "GENERATING STATION",
      sortable: true,
      className: "font-semibold text-[#19222D]",
    },
    {
      key: "energy_category",
      header: "CATEGORY",
      sortable: true,
    },
    {
      key: "mean_dispatched_mw",
      header: "MEAN MW",
      sortable: true,
      align: "right",
      accessor: (r) => formatMW(r.mean_dispatched_mw, 1),
    },
    {
      key: "stddev_dispatched_mw",
      header: "STD DEV",
      sortable: true,
      align: "right",
      accessor: (r) => formatMW(r.stddev_dispatched_mw, 1),
    },
    {
      key: "coefficient_of_variation",
      header: "CV (VOLATILITY)",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const raw = toNumeric(r.coefficient_of_variation);
        if (raw === null) return "—";
        const pct = raw * 100;
        const isStable = pct < 15;
        return (
          <span
            className={`px-2 py-0.5 rounded-[6px] text-[11px] font-bold ${
              isStable
                ? "bg-[#E8F6F2] text-[#177763]"
                : pct < 45
                ? "bg-[#FFF6E8] text-[#9A6715]"
                : "bg-[#FDEDEC] text-[#B03A2E]"
            }`}
          >
            {pct.toFixed(1)}%
          </span>
        );
      },
    },
    {
      key: "operational_behavior_class",
      header: "BEHAVIOR PROFILE",
      sortable: true,
      accessor: (r) => (
        <span className="text-[11px] font-semibold text-[#637185]">
          {r.operational_behavior_class}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Member 2 / Dispatch & Grid Dynamics"
        title="Dispatch & Grid Dynamics"
        titleAccent="."
        description="Diurnal 15-minute load curves, ramp-rate grid velocities, and plant dispatch volatility across 96 daily intervals during March 2024."
        onExportCsv={() => window.open("/api/exports/Q05", "_blank")}
      />

      {/* KPI row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="March Peak System Demand"
          value="2,674.00"
          unit="MW"
          period="Interval 78 (19:30)"
          sourcePill="Q05"
          accentColor="#19222D"
        />
        <KpiCard
          name="Weekday Morning Valley"
          value="1,408.00"
          unit="MW"
          period="Interval 16 (04:00)"
          sourcePill="Q05"
          accentColor="#4278B9"
        />
        <KpiCard
          name="Max 15-Min Ramp-Up"
          value="142.50"
          unit="MW"
          period="Evening Surge (18:15)"
          sourcePill="Q06"
          accentColor="#E9A43B"
        />
        <KpiCard
          name="Lakvijaya Stability (CV)"
          value="3.90"
          unit="%"
          period="Continuous Baseload"
          sourcePill="Q07"
          accentColor="#229C88"
        />
      </section>

      {/* 96-Interval Diurnal Load Curve */}
      <DiurnalLoadCurveChart data={diurnalData} />

      {/* Baseload vs Peaker Volatility Table */}
      {loading ? (
        <div className="py-12 text-center text-[#9AA5B0]">Loading volatility metrics...</div>
      ) : (
        <DataTable
          title="Baseload vs Peaker Operational Volatility"
          subtitle="Ranked by Coefficient of Variation (CV = StdDev / Mean MW). Lower CV indicates steady continuous baseload; higher CV indicates cycling peaker operation."
          badge="PUCSL · Q07"
          data={volatilityData}
          columns={columns}
          filename="gridlens-plant-volatility-Q07.csv"
        />
      )}
    </div>
  );
}
