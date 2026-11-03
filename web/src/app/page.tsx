"use client";

import React, { useState, useEffect, useMemo } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SalesTrendChart } from "@/components/charts/sales-trend-chart";
import { GenerationDonutChart } from "@/components/charts/generation-donut-chart";
import { CoverageIndicator } from "@/components/dashboard/coverage-indicator";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { toNumeric } from "@/lib/formatting/units";
import { Calendar, ShieldCheck, FilterX } from "lucide-react";

interface SalesRecord {
  year: number;
  total_sales: number;
  productive_sector: number;
  residential: number;
  productive_share: number;
  [key: string]: unknown;
}

interface GenerationMixRecord {
  energy_category: string;
  fuel_type: string;
  total_energy_mwh: number | string;
  generation_share_pct: number | string;
  [key: string]: unknown;
}

const DEFAULT_SALES_RECORDS: SalesRecord[] = [
  { year: 2020, total_sales: 14287.0, productive_sector: 7194.0, residential: 5090.0, productive_share: 50.35 },
  { year: 2021, total_sales: 15214.0, productive_sector: 7939.0, residential: 5238.0, productive_share: 52.18 },
  { year: 2022, total_sales: 14520.0, productive_sector: 7541.0, residential: 5044.0, productive_share: 51.94 },
  { year: 2023, total_sales: 14153.5, productive_sector: 7731.5, residential: 4495.0, productive_share: 54.63 },
  { year: 2024, total_sales: 15190.5, productive_sector: 8452.5, residential: 4701.0, productive_share: 55.64 },
];

export default function OverviewPage() {
  const [selectedYear, setSelectedYear] = useState<string>("all");
  const [salesRecords, setSalesRecords] = useState<SalesRecord[]>(DEFAULT_SALES_RECORDS);
  const [generationData, setGenerationData] = useState<GenerationMixRecord[]>([]);
  const [sourceMode, setSourceMode] = useState<"live" | "snapshot">("snapshot");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/Q01").then((res) => res.json()),
      fetch("/api/analytics/Q21").then((res) => res.json()),
    ])
      .then(([q01Res, q21Res]) => {
        if (q01Res.success && Array.isArray(q01Res.data)) {
          setGenerationData(q01Res.data);
          if (q01Res.sourceMode) setSourceMode(q01Res.sourceMode);
        }
        if (q21Res.success && Array.isArray(q21Res.data) && q21Res.data.length > 0) {
          // Parse Q21 GROUPING SETS into yearly sales records
          const yearMap = new Map<number, { total: number; productive: number; residential: number }>();
          q21Res.data.forEach((r: Record<string, unknown>) => {
            const yr = Number(r.calendar_year);
            if (!yr) return;
            const current = yearMap.get(yr) || { total: 0, productive: 0, residential: 0 };
            const mwh = toNumeric(r.total_sales_gwh as string | number | null | undefined) || 0;
            const classification = String(r.economic_classification || "").toUpperCase();

            if (classification.includes("PRODUCTIVE")) {
              current.productive += mwh;
            } else if (classification.includes("RESIDENTIAL") || classification.includes("DOMESTIC")) {
              current.residential += mwh;
            }
            if (classification.includes("TOTAL") || r.sector_code === "ALL") {
              current.total = mwh;
            }
            yearMap.set(yr, current);
          });

          if (yearMap.size >= 5) {
            const parsed = Array.from(yearMap.entries())
              .sort(([a], [b]) => a - b)
              .map(([year, val]) => ({
                year,
                total_sales: val.total || (val.productive + val.residential),
                productive_sector: val.productive,
                residential: val.residential,
                productive_share: val.total > 0 ? (val.productive / val.total) * 100 : 50,
              }));
            setSalesRecords(parsed);
          }
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load overview analytics:", err);
        setLoading(false);
      });
  }, []);

  // Compute dynamic KPIs
  const kpis = useMemo(() => {
    let coalMWh = 595524.5;
    let oilMWh = 387450.75;
    let hydroMWh = 321595.5;

    const coal = generationData.find((g) => g.energy_category?.toLowerCase().includes("coal"));
    if (coal) coalMWh = toNumeric(coal.total_energy_mwh) || coalMWh;

    const oil = generationData.find((g) => g.energy_category?.toLowerCase().includes("oil"));
    if (oil) oilMWh = toNumeric(oil.total_energy_mwh) || oilMWh;

    const hydro = generationData.find((g) => g.energy_category?.toLowerCase().includes("hydro"));
    if (hydro) hydroMWh = toNumeric(hydro.total_energy_mwh) || hydroMWh;

    const latestYearRecord = salesRecords.find((r) => r.year === 2024) || salesRecords[salesRecords.length - 1];
    const latestSales = latestYearRecord ? latestYearRecord.total_sales : 15190.5;

    return {
      coalMWh,
      oilMWh,
      hydroMWh,
      latestSales,
    };
  }, [generationData, salesRecords]);

  const filteredSales = useMemo(() => {
    return selectedYear === "all"
      ? salesRecords
      : salesRecords.filter((r) => String(r.year) === selectedYear);
  }, [salesRecords, selectedYear]);

  const columns: ColumnDef<SalesRecord>[] = [
    {
      key: "year",
      header: "YEAR",
      sortable: true,
      className: "font-bold text-[#19222D]",
    },
    {
      key: "total_sales",
      header: "TOTAL SALES (GWH)",
      sortable: true,
      align: "right",
      accessor: (r) =>
        r.total_sales.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
    },
    {
      key: "productive_sector",
      header: "PRODUCTIVE SECTOR (GWH)",
      sortable: true,
      align: "right",
      accessor: (r) =>
        r.productive_sector.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
    },
    {
      key: "residential",
      header: "RESIDENTIAL (GWH)",
      sortable: true,
      align: "right",
      accessor: (r) =>
        r.residential.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
    },
    {
      key: "productive_share",
      header: "PRODUCTIVE SHARE",
      sortable: true,
      align: "right",
      accessor: (r) => (
        <span className="px-2 py-0.5 rounded-[6px] bg-[#E8F6F2] text-[#177763] text-[11px] font-bold">
          {r.productive_share.toFixed(2)}%
        </span>
      ),
    },
  ];

  const handleExportCsv = () => {
    const header = "Year,Total Sales (GWh),Productive Sector (GWh),Residential (GWh),Productive Share (%)\n";
    const rows = filteredSales
      .map(
        (r) =>
          `${r.year},${r.total_sales},${r.productive_sector},${r.residential},${r.productive_share}`
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `gridlens-ceb-sales-${selectedYear === "all" ? "2020-2024" : selectedYear}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <PageHeader
        eyebrow="GridLens / National energy intelligence"
        title="Energy analytics"
        titleAccent="."
        description="Explore Sri Lanka’s electricity generation, sectoral sales and data coverage. Built from historical CEB, PUCSL and NASA POWER observations."
        onExportCsv={handleExportCsv}
      >
        <div className="flex items-center gap-2">
          <span
            className={`px-2.5 py-1 rounded-[8px] text-[11px] font-bold uppercase tracking-wider inline-flex items-center gap-1.5 ${
              sourceMode === "live"
                ? "bg-[#E8F6F2] text-[#177763] border border-[#229C88]/30"
                : "bg-[#FFF6E8] text-[#9A6715] border border-[#E9A43B]/30"
            }`}
          >
            <ShieldCheck size={13} />
            {sourceMode === "live" ? "Live PostgreSQL" : "Verified Snapshot"}
          </span>

          <label className="h-[41px] px-3.5 rounded-[10px] bg-white border border-[#E2E7EE] hover:border-[#CBD4DF] text-[#435166] text-[12px] font-semibold inline-flex items-center gap-2 cursor-pointer transition-colors">
            <Calendar size={15} className="text-[#748091]" />
            <span>Sales year</span>
            <select
              id="yearFilter"
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="bg-transparent border-none text-[#19222D] font-bold text-[12px] cursor-pointer outline-none ml-1"
            >
              <option value="all">2020–2024</option>
              <option value="2020">2020</option>
              <option value="2021">2021</option>
              <option value="2022">2022</option>
              <option value="2023">2023</option>
              <option value="2024">2024</option>
            </select>
          </label>
        </div>
      </PageHeader>

      {/* KPI Cards Grid */}
      <section aria-label="Key historical metrics" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="Coal generation"
          value={kpis.coalMWh.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          unit="MWh"
          period="March 2024"
          sourcePill="PUCSL"
          accentColor="#343D49"
        />
        <KpiCard
          name="Oil generation"
          value={kpis.oilMWh.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          unit="MWh"
          period="March 2024"
          sourcePill="PUCSL"
          accentColor="#E9A43B"
        />
        <KpiCard
          name="Major hydro generation"
          value={kpis.hydroMWh.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          unit="MWh"
          period="March 2024"
          sourcePill="PUCSL"
          accentColor="#4278B9"
        />
        <KpiCard
          name="2024 billed electricity sales"
          value={kpis.latestSales.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          unit="GWh"
          period="Calendar year 2024"
          sourcePill="CEB"
          accentColor="#229C88"
        />
      </section>

      {/* Main Analytical Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8">
          <SalesTrendChart />
        </div>
        <div className="lg:col-span-4">
          <GenerationDonutChart />
        </div>
      </div>

      {/* Sector Sales Table */}
      <DataTable
        title="Sales by Economic Sector"
        subtitle="Five years of sectoral sales and productive-sector contribution (CEB Audited Digests)"
        badge="CEB · Q09 & Q21"
        data={filteredSales}
        columns={columns}
        filename={`gridlens-sales-${selectedYear}.csv`}
      />

      {/* Warehouse Coverage Telemetry */}
      <CoverageIndicator />
    </div>
  );
}
