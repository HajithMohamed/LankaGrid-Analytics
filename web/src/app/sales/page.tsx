"use client";

import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { formatGWh, formatPercent, toNumeric } from "@/lib/formatting/units";

interface SectorGrowthRecord {
  sector_code: string;
  sector_name: string;
  tariff_group: string;
  sales_2020_gwh: number | string;
  sales_2021_gwh: number | string;
  sales_2022_gwh: number | string;
  sales_2023_gwh: number | string;
  sales_2024_gwh: number | string;
  net_5yr_change_gwh: number | string;
  net_5yr_change_pct: number | string | null;
  cagr_2020_2024_pct: number | string | null;
  growth_magnitude_rank: number;
  [key: string]: unknown;
}

export default function SalesPage() {
  const [growthData, setGrowthData] = useState<SectorGrowthRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/analytics/Q10")
      .then((res) => res.json())
      .then((res) => {
        if (res.success) setGrowthData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load Q10 sales analytics:", err);
        setLoading(false);
      });
  }, []);

  const columns: ColumnDef<SectorGrowthRecord>[] = [
    {
      key: "sector_name",
      header: "CONSUMPTION SECTOR",
      sortable: true,
      className: "font-bold text-[#19222D]",
    },
    {
      key: "tariff_group",
      header: "GROUP",
      sortable: true,
    },
    {
      key: "sales_2020_gwh",
      header: "2020 (GWH)",
      sortable: true,
      align: "right",
      accessor: (r) => formatGWh(r.sales_2020_gwh, 1),
    },
    {
      key: "sales_2022_gwh",
      header: "2022 CRISIS (GWH)",
      sortable: true,
      align: "right",
      accessor: (r) => formatGWh(r.sales_2022_gwh, 1),
    },
    {
      key: "sales_2024_gwh",
      header: "2024 (GWH)",
      sortable: true,
      align: "right",
      accessor: (r) => formatGWh(r.sales_2024_gwh, 1),
    },
    {
      key: "net_5yr_change_pct",
      header: "5-YR CHANGE",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const val = toNumeric(r.net_5yr_change_pct);
        if (val === null) return "—";
        const isPos = val >= 0;
        return (
          <span
            className={`px-2 py-0.5 rounded-[6px] text-[11px] font-bold ${
              isPos ? "bg-[#E8F6F2] text-[#177763]" : "bg-[#FDEDEC] text-[#B03A2E]"
            }`}
          >
            {isPos ? `+${val.toFixed(1)}%` : `${val.toFixed(1)}%`}
          </span>
        );
      },
    },
    {
      key: "cagr_2020_2024_pct",
      header: "CAGR (%)",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const val = toNumeric(r.cagr_2020_2024_pct);
        return val !== null
          ? `${val >= 0 ? "+" : ""}${val.toFixed(2)}%`
          : "—";
      },
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Member 3 / Consumer Demand & Tariff Analytics"
        title="Consumer Demand & Sales Analytics"
        titleAccent="."
        description="Historical electricity billing across consumer sectors, tariff elasticity, hotel tourism recovery (+83.94%), and bulk distribution to LECO (2020–2024)."
        onExportCsv={() => window.open("/api/exports/Q10", "_blank")}
      />

      {/* KPI row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="2024 Total Billed Sales"
          value="15,190.50"
          unit="GWh"
          period="Audited CEB"
          sourcePill="CEB"
          accentColor="#19222D"
        />
        <KpiCard
          name="Hotel Sector Rebound"
          value="+83.94"
          unit="%"
          period="Post-Crisis Surge"
          sourcePill="Q10"
          accentColor="#229C88"
        />
        <KpiCard
          name="Industrial Electricity"
          value="4,622.00"
          unit="GWh"
          period="30.4% Market Share"
          sourcePill="Q09"
          accentColor="#4278B9"
        />
        <KpiCard
          name="LECO Bulk Supply"
          value="1,625.00"
          unit="GWh"
          period="Distribution Licensee"
          sourcePill="Q12"
          accentColor="#E9A43B"
        />
      </section>

      {/* Sector Net Growth Visual */}
      <SimpleBarChart
        title="Five-Year Sectoral Demand Growth Trajectory (2020 vs 2024)"
        subtitle="Net percentage change in annual electricity sales across CEB tariff categories"
        badge="CEB Statistical Digest · Q10"
        unit="%"
        data={growthData
          .filter((d) => toNumeric(d.net_5yr_change_pct) !== null)
          .map((d) => {
            const pct = toNumeric(d.net_5yr_change_pct) || 0;
            const sales2024 = toNumeric(d.sales_2024_gwh) || 0;
            return {
              label: d.sector_name,
              value: Math.abs(pct),
              formattedValue: `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}% (${sales2024.toFixed(0)} GWh)`,
              sublabel: d.tariff_group,
              color:
                pct >= 20
                  ? "#229C88"
                  : pct >= 0
                  ? "#4278B9"
                  : "#D65F62",
            };
          })}
      />

      {/* Sector Sales Growth Table */}
      {loading ? (
        <div className="py-12 text-center text-[#9AA5B0]">Loading sales data...</div>
      ) : (
        <DataTable
          title="Five-Year Sectoral Sales & Post-Crisis Rebound Matrix"
          subtitle="Annual billed sales in GWh and Compound Annual Growth Rate (CAGR) from 2020 through 2024"
          badge="SQL Query Q10"
          data={growthData}
          columns={columns}
          filename="gridlens-sectoral-growth-Q10.csv"
        />
      )}
    </div>
  );
}
