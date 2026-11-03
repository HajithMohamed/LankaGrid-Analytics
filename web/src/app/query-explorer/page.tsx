"use client";

import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { DataTable } from "@/components/tables/data-table";
import { QUERY_REGISTRY, MEMBER_DOMAINS, QueryDefinition } from "@/lib/analytics/query-registry";
import {
  SEMANTIC_MEASURES,
  SEMANTIC_DIMENSIONS,
  validateMeasureDimensionGrain,
} from "@/lib/analytics/semantic-layer";
import {
  Code,
  Download,
  Copy,
  Check,
  Database,
  Layers,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  Search,
} from "lucide-react";

interface QueryResponse {
  success: boolean;
  queryId: string;
  definition: QueryDefinition;
  data: Record<string, unknown>[];
  rowCount: number;
  source: "live" | "snapshot";
  sourceMode?: "live" | "snapshot";
  executionTimeMs?: number;
  sqlText?: string;
  error?: string;
}

interface SemanticResult {
  success: boolean;
  measure: string;
  dimension: string;
  unit: string;
  sourceQuery: string;
  sourceMode?: string;
  results: Array<{ dimension: string; measure: number; unit: string }>;
  error?: string;
}

export default function QueryExplorerPage() {
  const [explorerTab, setExplorerTab] = useState<"sql" | "semantic">("sql");
  const [selectedId, setSelectedId] = useState<string>("Q01");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<"table" | "sql">("table");

  // Semantic layer state
  const [selectedMeasure, setSelectedMeasure] = useState<string>("generation_mwh");
  const [selectedDimension, setSelectedDimension] = useState<string>("energy_category");
  const [semanticResult, setSemanticResult] = useState<SemanticResult | null>(null);
  const [semanticLoading, setSemanticLoading] = useState<boolean>(false);

  const activeDef = QUERY_REGISTRY[selectedId] || QUERY_REGISTRY["Q01"];

  useEffect(() => {
    let isCurrent = true;
    setLoading(true);

    fetch(`/api/analytics/${selectedId}`)
      .then((res) => res.json())
      .then((data: QueryResponse) => {
        if (isCurrent) {
          setQueryResult(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isCurrent) {
          console.error("Failed to load query data:", err);
          setLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedId]);

  const handleCopySql = () => {
    if (queryResult?.sqlText) {
      navigator.clipboard.writeText(queryResult.sqlText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const grainValidation = validateMeasureDimensionGrain(selectedMeasure, selectedDimension);

  const handleRunSemanticQuery = () => {
    if (!grainValidation.compatible) return;
    setSemanticLoading(true);

    fetch("/api/analytics/semantic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        measureId: selectedMeasure,
        dimensionId: selectedDimension,
      }),
    })
      .then((res) => res.json())
      .then((data: SemanticResult) => {
        setSemanticResult(data);
        setSemanticLoading(false);
      })
      .catch((err) => {
        console.error("Semantic query failed:", err);
        setSemanticLoading(false);
      });
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Academic OLAP & Semantic Intelligence"
        title="Query & Analytics Explorer"
        titleAccent="."
        description="Inspect all 24 team SQL queries across six analytical domains, verify Kimball fact/dimension grains, and query controlled semantic metrics."
      >
        {/* Tab switcher: SQL Registry vs Semantic Query */}
        <div className="inline-flex rounded-lg border border-[#E2E7EE] p-0.5 bg-[#F8F9FB]">
          <button
            type="button"
            onClick={() => setExplorerTab("sql")}
            className={`px-3 py-1.5 rounded-md text-[12px] font-semibold transition-colors flex items-center gap-1.5 ${
              explorerTab === "sql"
                ? "bg-white text-[#19222D] shadow-sm"
                : "text-[#748091] hover:text-[#19222D]"
            }`}
          >
            <Database size={13} />
            <span>24 SQL Queries</span>
          </button>
          <button
            type="button"
            onClick={() => setExplorerTab("semantic")}
            className={`px-3 py-1.5 rounded-md text-[12px] font-semibold transition-colors flex items-center gap-1.5 ${
              explorerTab === "semantic"
                ? "bg-white text-[#19222D] shadow-sm"
                : "text-[#748091] hover:text-[#19222D]"
            }`}
          >
            <Sparkles size={13} className="text-[#E9A43B]" />
            <span>Semantic Layer (Governed)</span>
          </button>
        </div>
      </PageHeader>

      {explorerTab === "sql" ? (
        <div className="space-y-6">
          {/* Domain Query Selector Bar */}
          <div className="card-glass p-5">
            <div className="text-[11px] font-bold uppercase tracking-wider text-[#9AA5B0] mb-3">
              Select Analytical Query by Research Domain
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {MEMBER_DOMAINS.map((domain) => (
                <div
                  key={domain.member}
                  className="p-3 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0]"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-bold text-[#19222D]">
                      {domain.member}: {domain.name}
                    </span>
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: domain.color }}
                    />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {domain.queries.map((qId) => {
                      const isSelected = selectedId === qId;
                      return (
                        <button
                          key={qId}
                          type="button"
                          onClick={() => setSelectedId(qId)}
                          className={`px-2.5 py-1 rounded text-[11px] font-bold font-mono transition-colors ${
                            isSelected
                              ? "bg-[#19222D] text-white shadow-sm"
                              : "bg-white border border-[#E7EBF0] text-[#465469] hover:bg-[#F0F3F7] hover:text-[#19222D]"
                          }`}
                        >
                          {qId}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Selected Query Details Card */}
          <div className="card-glass p-6">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#EEF1F4]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[12px] font-bold px-2.5 py-0.5 rounded-md bg-[#19222D] text-white">
                    {activeDef.id}
                  </span>
                  <h2 className="text-[20px] font-bold text-[#19222D] tracking-[-0.5px] m-0">
                    {activeDef.title}
                  </h2>
                </div>
                <p className="text-[13px] text-[#637185] mt-1 m-0">
                  {activeDef.businessQuestion}
                </p>
              </div>

              {/* View Mode Toggle & Export */}
              <div className="flex items-center gap-2">
                <div className="inline-flex rounded-lg border border-[#E2E7EE] p-0.5 bg-[#F8F9FB]">
                  <button
                    type="button"
                    onClick={() => setViewMode("table")}
                    className={`px-3 py-1.5 rounded-md text-[12px] font-semibold transition-colors ${
                      viewMode === "table"
                        ? "bg-white text-[#19222D] shadow-sm"
                        : "text-[#748091] hover:text-[#19222D]"
                    }`}
                  >
                    Table View
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("sql")}
                    className={`px-3 py-1.5 rounded-md text-[12px] font-semibold transition-colors flex items-center gap-1.5 ${
                      viewMode === "sql"
                        ? "bg-white text-[#19222D] shadow-sm"
                        : "text-[#748091] hover:text-[#19222D]"
                    }`}
                  >
                    <Code size={13} />
                    <span>SQL Source</span>
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => window.open(`/api/exports/${selectedId}`, "_blank")}
                  className="h-[34px] px-3 bg-white border border-[#E2E7EE] hover:bg-[#F9FBFD] rounded-lg text-[12px] font-semibold text-[#435166] inline-flex items-center gap-1.5 transition-colors"
                >
                  <Download size={13} />
                  <span>CSV</span>
                </button>
              </div>
            </div>

            {/* Metadata Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-4 text-[12px] border-b border-[#EEF1F4]">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-[#9AA5B0]">
                  Domain Lead
                </div>
                <div className="font-semibold text-[#19222D] mt-0.5">
                  {activeDef.member} ({activeDef.memberName})
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-[#9AA5B0]">
                  Primary Fact Table
                </div>
                <div className="font-semibold text-[#19222D] mt-0.5 font-mono text-[11px]">
                  {activeDef.facts.join(", ")}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-[#9AA5B0]">
                  Reporting Grain
                </div>
                <div className="font-semibold text-[#19222D] mt-0.5">
                  {activeDef.period}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-[#9AA5B0]">
                  Execution Mode
                </div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      queryResult?.source === "live"
                        ? "bg-[#229C88]"
                        : "bg-[#E9A43B]"
                    }`}
                  />
                  <span className="font-semibold text-[#19222D]">
                    {queryResult?.source === "live" ? "PostgreSQL 18 Live" : "Authentic Snapshot"}
                  </span>
                  {queryResult?.executionTimeMs !== undefined && (
                    <span className="text-[#86919E] text-[11px]">
                      ({queryResult.executionTimeMs} ms)
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Academic OLAP Technique Banner */}
            <div className="py-3 px-4 my-4 rounded-[10px] bg-[#F8F9FB] border border-[#E7EBF0] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[12px]">
              <div className="flex items-start sm:items-center gap-2">
                <span className="px-2 py-0.5 rounded-[5px] bg-[#19222D] text-white text-[10px] font-bold tracking-wider uppercase shrink-0">
                  OLAP Technique
                </span>
                <span className="font-semibold text-[#19222D]">
                  {activeDef.olapTechnique}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-[#748091] shrink-0">
                <Layers size={13} className="text-[#4278B9]" />
                <span>Dimensions: {activeDef.dimensions.join(", ")}</span>
              </div>
            </div>

            {/* Content Body: Table or SQL Text */}
            <div>
              {viewMode === "sql" ? (
                <div className="relative">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#E7EBF0]">
                    <span className="text-[11px] font-bold text-[#748091]">
                      File: {activeDef.sqlRelativePath}
                    </span>
                    <button
                      type="button"
                      onClick={handleCopySql}
                      className="px-2.5 py-1 rounded bg-[#F8F9FB] border border-[#E2E7EE] hover:bg-[#EEF1F4] text-[11px] font-semibold text-[#465469] inline-flex items-center gap-1.5"
                    >
                      {copied ? <Check size={12} className="text-[#229C88]" /> : <Copy size={12} />}
                      <span>{copied ? "Copied" : "Copy SQL"}</span>
                    </button>
                  </div>
                  <pre className="p-4 rounded-lg bg-[#19222D] text-[#E7EBF0] text-[12px] font-mono overflow-x-auto leading-relaxed max-h-[500px]">
                    {queryResult?.sqlText || "-- SQL text loading..."}
                  </pre>
                </div>
              ) : loading ? (
                <div className="py-16 text-center text-[#9AA5B0]">
                  Executing query {selectedId}...
                </div>
              ) : queryResult && queryResult.data.length > 0 ? (
                <DataTable
                  title={`${activeDef.id} Output Dataset`}
                  subtitle={`Showing ${queryResult.rowCount} rows returned`}
                  badge={activeDef.period}
                  data={queryResult.data}
                  filename={`gridlens-${selectedId}-dataset.csv`}
                />
              ) : (
                <div className="py-16 text-center text-[#9AA5B0]">
                  No records returned for query {selectedId}.
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Governed Semantic Layer */
        <div className="space-y-6">
          <div className="card-glass p-6">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles size={16} className="text-[#E9A43B]" />
                  <h2 className="text-[18px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
                    Governed Power BI-Style Semantic Modeling
                  </h2>
                </div>
                <p className="text-[13px] text-[#64748B] mt-1 m-0">
                  Select a standardized business measure and dimension. The semantic layer validates dimensional grain compatibility and enforces physical unit safety (MW rate vs MWh energy).
                </p>
              </div>
              <span className="text-[11px] font-bold text-[#177763] px-2.5 py-1 border border-[#229C88]/30 rounded-[7px] bg-[#E8F6F2]">
                Strictly Governed
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-6">
              {/* Measure Selection */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#748091] mb-2">
                  Business Measure
                </label>
                <div className="space-y-2">
                  {Object.values(SEMANTIC_MEASURES).map((m) => (
                    <label
                      key={m.id}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedMeasure === m.id
                          ? "bg-[#FFF6E8] border-[#E9A43B]"
                          : "bg-white border-[#E2E7EE] hover:bg-[#F8F9FB]"
                      }`}
                    >
                      <input
                        type="radio"
                        name="measure"
                        value={m.id}
                        checked={selectedMeasure === m.id}
                        onChange={(e) => setSelectedMeasure(e.target.value)}
                        className="mt-1 accent-[#E9A43B]"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[13px] font-bold text-[#19222D]">
                            {m.name}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-white text-[#748091] border border-[#E7EBF0]">
                            {m.unit}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#64748B] mt-0.5 m-0">
                          {m.description}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Dimension Selection */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#748091] mb-2">
                  Analysis Dimension
                </label>
                <div className="space-y-2">
                  {Object.values(SEMANTIC_DIMENSIONS).map((d) => (
                    <label
                      key={d.id}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedDimension === d.id
                          ? "bg-[#EAF2FA] border-[#4278B9]"
                          : "bg-white border-[#E2E7EE] hover:bg-[#F8F9FB]"
                      }`}
                    >
                      <input
                        type="radio"
                        name="dimension"
                        value={d.id}
                        checked={selectedDimension === d.id}
                        onChange={(e) => setSelectedDimension(e.target.value)}
                        className="mt-1 accent-[#4278B9]"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[13px] font-bold text-[#19222D]">
                            {d.name}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-[#64748B] bg-white border border-[#E7EBF0]">
                            {d.dimensionTable}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#64748B] mt-0.5 m-0">
                          {d.allowedValues ? `${d.allowedValues.length} allowed categories (${d.allowedValues.slice(0, 3).join(", ")}...)` : "Promoted dimensional entities"}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Grain Compatibility & Execution Trigger */}
            <div className="p-4 rounded-lg bg-[#F8F9FB] border border-[#E7EBF0] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-[12px]">
                {grainValidation.compatible ? (
                  <>
                    <ShieldCheck size={18} className="text-[#229C88]" />
                    <span className="font-semibold text-[#19222D]">
                      Valid Kimball grain combination: {grainValidation.reason}
                    </span>
                  </>
                ) : (
                  <>
                    <ShieldAlert size={18} className="text-[#D65F62]" />
                    <span className="font-semibold text-[#D65F62]">
                      Invalid grain pairing: {grainValidation.reason}
                    </span>
                  </>
                )}
              </div>

              <button
                type="button"
                disabled={!grainValidation.compatible || semanticLoading}
                onClick={handleRunSemanticQuery}
                className="h-[38px] px-5 rounded-[8px] bg-[#19222D] hover:bg-[#303C4A] disabled:opacity-40 text-white text-[12px] font-bold inline-flex items-center gap-2 transition-colors cursor-pointer"
              >
                {semanticLoading ? (
                  <span>Aggregating...</span>
                ) : (
                  <>
                    <Search size={14} />
                    <span>Run Semantic Aggregation</span>
                  </>
                )}
              </button>
            </div>

            {/* Semantic Result Display */}
            {semanticResult && (
              <div className="mt-6 pt-6 border-t border-[#EEF1F4]">
                {semanticResult.success ? (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="text-[15px] font-bold text-[#19222D] m-0">
                          {semanticResult.measure} by {semanticResult.dimension}
                        </h3>
                        <p className="text-[11px] text-[#86919E] mt-0.5 m-0">
                          Standardized Unit: {semanticResult.unit} · Promoted via {semanticResult.sourceQuery}
                        </p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-[#E8F6F2] text-[#177763]">
                        {semanticResult.results.length} Categories
                      </span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-[13px] border-collapse">
                        <thead>
                          <tr className="border-b border-[#E7EBF0] bg-[#F8F9FB] text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                            <th className="py-2.5 px-3">Category</th>
                            <th className="py-2.5 px-3 text-right">Measure Value</th>
                            <th className="py-2.5 px-3 text-right">Unit</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#EEF1F4]">
                          {semanticResult.results.map((row, idx) => (
                            <tr key={idx} className="hover:bg-[#F9FBFD]">
                              <td className="py-2.5 px-3 font-semibold text-[#19222D]">
                                {row.dimension}
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono font-bold text-[#19222D]">
                                {row.measure.toLocaleString("en-US", {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2,
                                })}
                              </td>
                              <td className="py-2.5 px-3 text-right text-[11px] text-[#748091] font-mono">
                                {row.unit}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-[#FDEDEC] text-[#B03A2E] text-[12px]">
                    Semantic aggregation error: {semanticResult.error}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
