"use client";

import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { DataTable } from "@/components/tables/data-table";
import { QUERY_REGISTRY, MEMBER_DOMAINS, QueryDefinition } from "@/lib/analytics/query-registry";
import { Code, Download, Copy, Check, Database, Layers, Sparkles } from "lucide-react";

interface QueryResponse {
  success: boolean;
  queryId: string;
  definition: QueryDefinition;
  data: Record<string, unknown>[];
  rowCount: number;
  source: "live" | "snapshot";
  executionTimeMs?: number;
  sqlText?: string;
  error?: string;
}

export default function QueryExplorerPage() {
  const [selectedId, setSelectedId] = useState<string>("Q01");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<"table" | "sql">("table");

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

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Interactive SQL Engine"
        title="Warehouse Query Explorer"
        titleAccent="."
        description="Execute and inspect all 24 authoritative business analytical SQL queries across the six dimensional research domains."
        onExportCsv={() => window.open(`/api/exports/${selectedId}`, "_blank")}
      />

      {/* Query Selector Tabs by Member */}
      <div className="space-y-3">
        <div className="text-[11px] font-extrabold uppercase tracking-wider text-[#9AA5B0]">
          Select Query by Research Domain:
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {MEMBER_DOMAINS.map((domain) => (
            <div
              key={domain.member}
              className="card-glass p-3.5 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span
                    className="text-[11px] font-bold px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: `${domain.color}15`,
                      color: domain.color,
                    }}
                  >
                    {domain.member}
                  </span>
                  <span className="text-[11px] font-semibold text-[#86919E]">
                    {domain.name}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5 mt-2">
                {domain.queries.map((qId) => {
                  const isSelected = selectedId === qId;
                  return (
                    <button
                      key={qId}
                      type="button"
                      onClick={() => {
                        setSelectedId(qId);
                        setViewMode("table");
                      }}
                      className={`px-3 py-1.5 rounded-lg text-[12px] font-bold transition-all duration-150 ${
                        isSelected
                          ? "bg-[#19222D] text-white shadow-sm"
                          : "bg-[#F8F9FB] border border-[#E7EBF0] text-[#465469] hover:bg-[#F0F3F7] hover:text-[#19222D]"
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
              Data Source
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

        {/* Content Body: Table or SQL Text */}
        <div className="pt-4">
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
              filename={`gridlens-${selectedId}.csv`}
            />
          ) : (
            <div className="py-16 text-center text-[#9AA5B0]">
              No rows returned for {selectedId}.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
