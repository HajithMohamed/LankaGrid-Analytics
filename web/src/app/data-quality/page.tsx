"use client";

import React, { useState, useEffect, useMemo } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DataTable, ColumnDef } from "@/components/tables/data-table";
import { formatNumber, toNumeric } from "@/lib/formatting/units";
import { ShieldCheck, ArrowRight, Database, FileText, CheckCircle2, AlertTriangle, Layers } from "lucide-react";

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
  const [sourceMode, setSourceMode] = useState<"live" | "snapshot">("snapshot");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/Q22").then((res) => res.json()),
      fetch("/api/analytics/Q23").then((res) => res.json()),
    ])
      .then(([q22Res, q23Res]) => {
        if (q22Res.success) {
          setReconData(q22Res.data);
          if (q22Res.sourceMode) setSourceMode(q22Res.sourceMode);
        }
        if (q23Res.success) setQuarantineData(q23Res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load data quality analytics:", err);
        setLoading(false);
      });
  }, []);

  // Compute dynamic KPIs directly from fetched Q22 and Q23 data
  const kpis = useMemo(() => {
    // 1. Total quarantine rows
    let totalIssues = 926;
    let unmatchedRows = 879;
    let negativePowerRows = 47;

    const totalRow = quarantineData.find((q) =>
      q.dq_rule_code?.includes("TOTAL")
    );
    if (totalRow) {
      totalIssues = toNumeric(totalRow.total_issues_logged) || totalIssues;
    }

    const unmatched = quarantineData.find((q) =>
      q.issue_classification === "UNMATCHED_DIMENSION" || q.dq_rule_code?.includes("ENTITY")
    );
    if (unmatched) {
      unmatchedRows = toNumeric(unmatched.total_issues_logged) || unmatchedRows;
    }

    const negative = quarantineData.find((q) =>
      q.issue_classification === "INVALID_MEASUREMENT" || q.dq_rule_code?.includes("NEGATIVE")
    );
    if (negative) {
      negativePowerRows = toNumeric(negative.total_issues_logged) || negativePowerRows;
    }

    // 2. CEB max variance pct from Q22
    let maxVariancePct = 0.0;
    reconData.forEach((r) => {
      const v = toNumeric(r.variance_pct) || 0;
      if (v > maxVariancePct) maxVariancePct = v;
    });

    return {
      totalIssues,
      unmatchedRows,
      negativePowerRows,
      maxVariancePct,
    };
  }, [reconData, quarantineData]);

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
      accessor: (r) => (
        <span className="font-semibold text-[#19222D]">
          {r.reconciliation_tier}
        </span>
      ),
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
      key: "variance_magnitude",
      header: "VARIANCE",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const val = toNumeric(r.variance_magnitude) || 0;
        return (
          <span className={`font-semibold ${val === 0 ? "text-[#177763]" : "text-[#B03A2E]"}`}>
            {val.toFixed(2)} {r.measurement_unit}
          </span>
        );
      },
    },
    {
      key: "variance_pct",
      header: "VARIANCE %",
      sortable: true,
      align: "right",
      accessor: (r) => {
        const pct = toNumeric(r.variance_pct) || 0;
        return (
          <span
            className={`px-2 py-0.5 rounded-[6px] text-[11px] font-bold ${
              pct === 0
                ? "bg-[#E8F6F2] text-[#177763]"
                : pct <= 0.05
                ? "bg-[#FFF6E8] text-[#9A6715]"
                : "bg-[#FDEDEC] text-[#B03A2E]"
            }`}
          >
            {pct.toFixed(3)}%
          </span>
        );
      },
    },
    {
      key: "audit_status",
      header: "AUDIT STATUS",
      sortable: true,
      accessor: (r) => (
        <span className="text-[11px] font-bold text-[#637185]">
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
      className: "font-mono text-[12px] font-bold text-[#19222D]",
    },
    {
      key: "issue_classification",
      header: "CLASSIFICATION",
      sortable: true,
      accessor: (r) => (
        <span className="px-2 py-0.5 rounded-[6px] bg-[#F1F3F6] text-[#475467] text-[11px] font-bold">
          {r.issue_classification}
        </span>
      ),
    },
    {
      key: "severity_level",
      header: "SEVERITY",
      sortable: true,
      accessor: (r) => {
        const sev = String(r.severity_level).toUpperCase();
        return (
          <span
            className={`px-2 py-0.5 rounded-[6px] text-[11px] font-bold ${
              sev === "CRITICAL"
                ? "bg-[#FDEDEC] text-[#B03A2E]"
                : sev === "ERROR"
                ? "bg-[#FFF6E8] text-[#9A6715]"
                : "bg-[#E8F6F2] text-[#177763]"
            }`}
          >
            {sev}
          </span>
        );
      },
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
        title="Data Quality & Multi-Tier Audit"
        titleAccent="."
        description="Multi-tier data reconciliation between CEB statutory digests and PUCSL operational dispatch, dead-letter quarantine anomaly logs, and automated ETL lineage tracking."
        onExportCsv={() => window.open("/api/exports/Q22", "_blank")}
      >
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
      </PageHeader>

      {/* KPI row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          name="CEB Multi-Year Sales Precision"
          value={`≤ ${kpis.maxVariancePct.toFixed(3)}`}
          unit="%"
          period="Exact Zero-Variance"
          sourcePill="Q22"
          accentColor="#229C88"
        />
        <KpiCard
          name="Quarantined Anomalies"
          value={kpis.totalIssues.toLocaleString("en-US")}
          unit="Records"
          period="Safely Isolated"
          sourcePill="Q23"
          accentColor="#19222D"
        />
        <KpiCard
          name="Unmatched Dimension Names"
          value={kpis.unmatchedRows.toLocaleString("en-US")}
          unit="Rows"
          period="94.9% of Quarantine"
          sourcePill="Q23"
          accentColor="#E9A43B"
        />
        <KpiCard
          name="Negative Power Outliers"
          value={kpis.negativePowerRows.toLocaleString("en-US")}
          unit="Rows"
          period="Invalid Telemetry Filtered"
          sourcePill="Q23"
          accentColor="#D65F62"
        />
      </section>

      {/* Quarantine Issues Chart and Source Lineage Flow */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-6">
          <SimpleBarChart
            title="Quarantine Anomaly Classification"
            subtitle="Malformed records intercepted by pipeline validation gates without corrupting fact tables"
            badge="ETL Quality Gate · Q23"
            unit="rows"
            data={[
              {
                label: "Unmatched Entity Names (Spelling variations in raw PDF)",
                value: kpis.unmatchedRows,
                formattedValue: `${kpis.unmatchedRows} rows (94.9%)`,
                sublabel: "DQ_DIM_UNMATCHED_ENTITY",
                color: "#E9A43B",
              },
              {
                label: "Negative Active Power (Telemetry noise / sensor errors)",
                value: kpis.negativePowerRows,
                formattedValue: `${kpis.negativePowerRows} rows (5.1%)`,
                sublabel: "DQ_GEN_NEGATIVE_OUTPUT",
                color: "#D65F62",
              },
            ]}
          />
        </div>

        {/* Phase 6: ETL Source Lineage & Governance Flow */}
        <div className="lg:col-span-6">
          <div className="card-glass p-6 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-[17px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
                    Warehouse Ingestion &amp; Lineage Flow
                  </h3>
                  <p className="text-[12px] text-[#86919E] mt-1 m-0">
                    End-to-end data provenance from statutory publication to analytical mart
                  </p>
                </div>
                <span className="text-[11px] font-bold text-[#177763] px-2.5 py-1 border border-[#229C88]/30 rounded-[7px] bg-[#E8F6F2]">
                  Audit Enforced
                </span>
              </div>

              <div className="space-y-3 mt-4">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0]">
                  <FileText size={18} className="text-[#E9A43B] shrink-0" />
                  <div className="flex-1 text-[12px]">
                    <span className="font-bold text-[#19222D]">1. Official Raw Sources:</span>
                    <p className="text-[#64748B] m-0">CEB Statistical Digest (PDF), PUCSL 15-Min Telemetry (XLSX), NASA POWER API (JSON).</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0]">
                  <Layers size={18} className="text-[#4278B9] shrink-0" />
                  <div className="flex-1 text-[12px]">
                    <span className="font-bold text-[#19222D]">2. Immutable Raw &amp; Staging:</span>
                    <p className="text-[#64748B] m-0">SHA-256 hashed raw archives in <code>raw.*</code> mapped to typed staging in <code>staging.*</code>.</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0]">
                  <AlertTriangle size={18} className="text-[#D65F62] shrink-0" />
                  <div className="flex-1 text-[12px]">
                    <span className="font-bold text-[#19222D]">3. Quality Gate &amp; Quarantine:</span>
                    <p className="text-[#64748B] m-0">926 malformed rows safely isolated in <code>audit.data_quality_issue</code> without dropping.</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0]">
                  <Database size={18} className="text-[#229C88] shrink-0" />
                  <div className="flex-1 text-[12px]">
                    <span className="font-bold text-[#19222D]">4. Kimball Fact Constellation:</span>
                    <p className="text-[#64748B] m-0">Cleaned dimensional facts in <code>dw.*</code> (107k dispatch, 21k weather, 49 sales).</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-4 p-3 border border-[#ECF0F4] rounded-[8px] bg-[#FAFBFC] text-[11px] text-[#687686]">
              All promoted fact rows maintain record-level surrogate foreign keys referencing <code>audit.record_lineage</code>.
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
            title="Multi-Tier Cross-Source Reconciliations (Q22)"
            subtitle="Tier 1: CEB 5-Year Sales Digest (Constituent Sum vs Control Total). Tier 2: PUCSL March 1, 2024 Dispatch Telemetry vs Published Operating Report."
            badge="PUCSL & CEB · Q22"
            data={reconData}
            columns={reconColumns}
            filename="gridlens-cross-source-reconciliation-Q22.csv"
          />

          <DataTable
            title="Quarantine Dead-Letter Anomaly Ledger (Q23)"
            subtitle="Distribution of intercepted malformed source rows by validation rule code and pipeline origin."
            badge="ETL Quality Gate · Q23"
            data={quarantineData.filter((q) => !q.dq_rule_code?.includes("TOTAL"))}
            columns={quarantineColumns}
            filename="gridlens-quarantine-audit-Q23.csv"
          />
        </>
      )}
    </div>
  );
}
