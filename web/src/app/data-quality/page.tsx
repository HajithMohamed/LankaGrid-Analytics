"use client";

import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { formatNumber, toNumeric } from "@/lib/formatting/units";

interface CrossSourceReconciliationRecord {
  calendar_year: number;
  reconciliation_tier: string;
  calculated_constituent_sum: number | string;
  published_control_total: number | string;
  measurement_unit: string;
  variance_magnitude: number | string;
  variance_pct: number | string;
  audit_status: string;
  [key: string]: unknown;
}

interface QuarantineRecord {
  dq_rule_code: string;
  issue_classification: string;
  severity_level: string;
  total_issues_logged: number | string;
  percentage_of_all_issues: number | string;
  affected_staging_tables: number | string;
  primary_affected_pipeline: string;
  [key: string]: unknown;
}

export default function DataQualityPage() {
  const [reconData, setReconData] = useState<CrossSourceReconciliationRecord[]>([]);
  const [quarantineData, setQuarantineData] = useState<QuarantineRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/Q22").then((res) => res.json()),
      fetch("/api/analytics/Q23").then((res) => res.json()),
    ])
      .then(([q22Res, q23Res]) => {
        if (q22Res.success) setReconData(q22Res.data);
        if (q23Res.success) setQuarantineData(q23Res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load data quality analytics:", err);
        setLoading(false);
      });
  }, []);

  const reconColumns: ColumnDef<CrossSourceReconciliationRecord>[] = [
    {
      key: "calendar_year",
      header: "YEAR",
      sortable: true,
      className: "font-bold text-[#19222D]",
    },
    {
      key: "reconciliation_tier",
      header: "RECONCILIATION TIER",
      sortable: true,
    },
    {
      key: "calculated_constituent_sum",
      header: "CALCULATED SUM",
      sortable: true,
      align: "right",
      accessor: (r) =>
        `${formatNumber(r.calculated_constituent_sum, 1)} ${r.measurement_unit}`,
    },
    {
      key: "published_control_total",
      header: "CONTROL TOTAL",
      sortable: true,
      align: "right",
      accessor: (r) =>
        `${formatNumber(r.published_control_total, 1)} ${r.measurement_unit}`,
    },
    {
      key: "variance_pct",
      header: "VARIANCE (%)",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const val = toNumeric(r.variance_pct) || 0;
        return (
          <span
            className={`px-2 py-0.5 rounded-[6px] text-[11px] font-bold ${
              val <= 0.05
                ? "bg-[#E8F6F2] text-[#177763]"
                : "bg-[#FFF6E8] text-[#9A6715]"
            }`}
          >
            {val.toFixed(3)}%
          </span>
        );
      },
    },
    {
      key: "audit_status",
      header: "AUDIT STATUS",
      sortable: true,
      accessor: (r) => (
        <span className="text-[11px] font-semibold text-[#465469]">
          {r.audit_status}
        </span>
      ),
    },
  ];

  const quarantineColumns: ColumnDef<QuarantineRecord>[] = [
    {
      key: "dq_rule_code",
      header: "RULE CODE",
      sortable: true,
      className: "font-bold text-[#19222D]",
    },
    {
      key: "issue_classification",
      header: "CLASSIFICATION",
      sortable: true,
    },
    {
      key: "severity_level",
      header: "SEVERITY",
      sortable: true,
    },
    {
      key: "total_issues_logged",
      header: "ISSUES LOGGED",
      sortable: true,
      align: "right",
      accessor: (r) => formatNumber(r.total_issues_logged, 0),
    },
    {
      key: "percentage_of_all_issues",
      header: "SHARE (%)",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const val = toNumeric(r.percentage_of_all_issues) || 0;
        return `${val.toFixed(1)}%`;
      },
    },
    {
      key: "primary_affected_pipeline",
      header: "PIPELINE SOURCE",
      sortable: true,
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Member 6 / Data Quality & Lineage"
        title="Data Quality & Cross-Source Audit"
        titleAccent="."
        description="Comprehensive audit reconciliation between CEB gross generation and billed sales, dead-letter quarantine anomaly logs, and ETL pipeline throughput."
        onExportCsv={() => window.open("/api/exports/Q22", "_blank")}
      />

      {/* KPI row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="CEB Reconciliation Precision"
          value="≤ 0.007"
          unit="%"
          period="Exact Zero-Variance"
          sourcePill="Q22"
          accentColor="#229C88"
        />
        <KpiCard
          name="Quarantined Anomalies"
          value="926"
          unit="Records"
          period="Safely Isolated"
          sourcePill="Q23"
          accentColor="#19222D"
        />
        <KpiCard
          name="Unmatched Dimension Names"
          value="879"
          unit="Rows"
          period="94.9% of Quarantine"
          sourcePill="Q23"
          accentColor="#E9A43B"
        />
        <KpiCard
          name="Negative Power Outliers"
          value="47"
          unit="Rows"
          period="Invalid Telemetry Filtered"
          sourcePill="Q23"
          accentColor="#D65F62"
        />
      </section>

      {/* Quarantine Issues Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-6">
          <SimpleBarChart
            title="Quarantine Anomaly Breakdown"
            subtitle="Malformed records intercepted by pipeline validation gates without corrupting facts"
            badge="ETL Quality Gate · Q23"
            unit="rows"
            data={[
              {
                label: "Unmatched Entity Names (Spelling variations in raw PDF)",
                value: 879,
                formattedValue: "879 rows (94.9%)",
                sublabel: "DQ_DIM_UNMATCHED_ENTITY",
                color: "#E9A43B",
              },
              {
                label: "Negative Active Power (Telemetry noise / sensor errors)",
                value: 47,
                formattedValue: "47 rows (5.1%)",
                sublabel: "DQ_GEN_NEGATIVE_OUTPUT",
                color: "#D65F62",
              },
            ]}
          />
        </div>

        <div className="lg:col-span-6">
          <div className="card-glass p-6 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-[17px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
                    Transmission &amp; Distribution Losses
                  </h3>
                  <p className="text-[12px] text-[#86919E] mt-1 m-0">
                    Gross generation vs billed retail sales residual
                  </p>
                </div>
                <span className="text-[11px] font-bold text-[#7D8896] px-2.5 py-1 border border-[#E7EBF0] rounded-[7px] bg-[#FAFBFC]">
                  8.8% – 9.6%
                </span>
              </div>

              <div className="space-y-3 text-[12px] text-[#465469] leading-relaxed">
                <p>
                  Comparing CEB total gross utility generation against audited billed end-use sales reveals an annual residual loss of <strong>8.8% to 9.6%</strong> across 2020–2024.
                </p>
                <div className="p-3.5 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0] space-y-1.5">
                  <div className="flex justify-between font-semibold text-[#19222D]">
                    <span>2024 Gross Generation:</span>
                    <span>16,742 GWh</span>
                  </div>
                  <div className="flex justify-between font-semibold text-[#19222D]">
                    <span>2024 Billed Retail Sales:</span>
                    <span>15,190.5 GWh</span>
                  </div>
                  <div className="flex justify-between font-bold text-[#229C88] pt-1 border-t border-[#E7EBF0]">
                    <span>Implied T&amp;D Loss Residual:</span>
                    <span>9.27% (1,551.5 GWh)</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-4 p-3 border border-[#ECF0F4] rounded-[8px] bg-[#FAFBFC] text-[11px] text-[#687686]">
              Matches official CEB engineering transmission loss benchmarks (9.0% ± 0.5%).
            </div>
          </div>
        </div>
      </div>

      {/* Cross-Source Reconciliation Table */}
      {loading ? (
        <div className="py-12 text-center text-[#9AA5B0]">Loading quality audit tables...</div>
      ) : (
        <>
          <DataTable
            title="Cross-Source Reconciliations & Audit Control Totals"
            subtitle="Verification of calculated constituent sums against published control totals (CEB Statistical Digest)"
            badge="SQL Query Q22"
            data={reconData}
            columns={reconColumns}
            filename="gridlens-cross-source-reconciliation-Q22.csv"
          />

          <DataTable
            title="Quarantine Dead-Letter Inspection Log"
            subtitle="Distribution of intercepted malformed source rows by validation rule code"
            badge="SQL Query Q23"
            data={quarantineData.filter((q) => q.dq_rule_code !== ">>> TOTAL WAREHOUSE QUALITY ISSUES <<<")}
            columns={quarantineColumns}
            filename="gridlens-quarantine-audit-Q23.csv"
          />
        </>
      )}
    </div>
  );
}
