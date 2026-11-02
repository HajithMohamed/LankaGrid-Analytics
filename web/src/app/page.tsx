"use client";

import React, { useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SalesTrendChart } from "@/components/charts/sales-trend-chart";
import { GenerationDonutChart } from "@/components/charts/generation-donut-chart";
import { CoverageIndicator } from "@/components/dashboard/coverage-indicator";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { Calendar } from "lucide-react";

interface SalesRecord {
  year: number;
  total_sales: number;
  productive_sector: number;
  residential: number;
  productive_share: number;
  [key: string]: unknown;
}

// Authentic Q21 and Q09 warehouse figures
const ALL_SALES_RECORDS: SalesRecord[] = [
  {
    year: 2020,
    total_sales: 14287.0,
    productive_sector: 7194.0,
    residential: 5090.0,
    productive_share: 50.35,
  },
  {
    year: 2021,
    total_sales: 15214.0,
    productive_sector: 7939.0,
    residential: 5238.0,
    productive_share: 52.18,
  },
  {
    year: 2022,
    total_sales: 14520.0,
    productive_sector: 7541.0,
    residential: 5044.0,
    productive_share: 51.94,
  },
  {
    year: 2023,
    total_sales: 14153.5,
    productive_sector: 7731.5,
    residential: 4495.0,
    productive_share: 54.63,
  },
  {
    year: 2024,
    total_sales: 15190.5,
    productive_sector: 8452.5,
    residential: 4701.0,
    productive_share: 55.64,
  },
];

export default function OverviewPage() {
  const [selectedYear, setSelectedYear] = useState<string>("all");

  const filteredSales =
    selectedYear === "all"
      ? ALL_SALES_RECORDS
      : ALL_SALES_RECORDS.filter((r) => String(r.year) === selectedYear);

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
      </PageHeader>

      {/* KPI Cards Grid */}
      <section aria-label="Key historical metrics" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="Coal generation"
          value="595,524.50"
          unit="MWh"
          period="March 2024"
          sourcePill="PUCSL"
          accentColor="#343D49"
        />
        <KpiCard
          name="Oil generation"
          value="387,450.75"
          unit="MWh"
          period="March 2024"
          sourcePill="PUCSL"
          accentColor="#E9A43B"
        />
        <KpiCard
          name="Major hydro generation"
          value="321,595.50"
          unit="MWh"
          period="March 2024"
          sourcePill="PUCSL"
          accentColor="#4278B9"
        />
        <KpiCard
          name="2024 billed electricity sales"
          value="15,190.50"
          unit="GWh"
          period="Calendar year 2024"
          sourcePill="CEB"
          accentColor="#229C88"
        />
      </section>

      {/* Primary Analytics Charts (8:4 grid) */}
      <section aria-label="Analytics charts" className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8">
          <SalesTrendChart
            data={ALL_SALES_RECORDS.map((r) => ({
              year: r.year,
              total: r.total_sales,
              productive: r.productive_sector,
              residential: r.residential,
              share: r.productive_share,
            }))}
            selectedYear={selectedYear}
            onSelectYear={(yr) => setSelectedYear(yr)}
          />
        </div>
        <div className="lg:col-span-4">
          <GenerationDonutChart />
        </div>
      </section>

      {/* Historical Data & Coverage Section */}
      <section aria-label="Historical records" className="space-y-4">
        <div className="flex items-baseline justify-between gap-4 pt-2">
          <div>
            <h2 className="text-[20px] font-bold text-[#19222D] tracking-[-0.65px] m-0">
              Explore Historical Records
            </h2>
            <p className="text-[12px] text-[#8190A0] mt-1 m-0">
              Verified warehouse figures · SQL query Q21 &amp; Q09
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-7">
            <DataTable
              title="Sales by Economic Sector"
              subtitle={
                selectedYear === "all"
                  ? "Five years of sectoral sales and productive-sector contribution"
                  : `Filtered view: ${selectedYear} sales and productive-sector contribution`
              }
              badge="GWh · 2020–2024"
              data={filteredSales}
              columns={columns}
              filename={`gridlens-sectoral-sales-${selectedYear}.csv`}
            />
          </div>
          <div className="lg:col-span-5">
            <CoverageIndicator />
          </div>
        </div>
      </section>
    </div>
  );
}
