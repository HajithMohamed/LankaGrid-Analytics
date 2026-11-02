"use client";

import React, { useState, useMemo } from "react";
import { Download, Search, ChevronLeft, ChevronRight, ArrowUpDown } from "lucide-react";

export interface ColumnDef<T> {
  key: string;
  header: string;
  accessor?: (row: T) => React.ReactNode;
  sortable?: boolean;
  align?: "left" | "center" | "right";
  className?: string;
}

interface DataTableProps<T extends Record<string, unknown>> {
  title: string;
  subtitle?: string;
  badge?: string;
  data: T[];
  columns?: ColumnDef<T>[];
  pageSize?: number;
  filename?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  title,
  subtitle,
  badge,
  data,
  columns,
  pageSize = 10,
  filename = "gridlens-export.csv",
}: DataTableProps<T>) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState(1);

  // Auto-detect columns if not explicitly provided
  const resolvedColumns: ColumnDef<T>[] = useMemo(() => {
    if (columns && columns.length > 0) return columns;
    if (!data || data.length === 0) return [];

    const keys = Object.keys(data[0]);
    return keys.map((k) => ({
      key: k,
      header: k.replace(/_/g, " ").toUpperCase(),
      sortable: true,
      align: typeof data[0][k] === "number" ? "right" : "left",
      accessor: (row: T) => {
        const val = row[k];
        if (typeof val === "number") {
          return val.toLocaleString("en-US", { maximumFractionDigits: 2 });
        }
        return String(val ?? "—");
      },
    }));
  }, [columns, data]);

  // Filter
  const filteredData = useMemo(() => {
    if (!searchTerm.trim()) return data;
    const lower = searchTerm.toLowerCase();
    return data.filter((row) =>
      Object.values(row).some((val) =>
        String(val ?? "").toLowerCase().includes(lower)
      )
    );
  }, [data, searchTerm]);

  // Sort
  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData;
    return [...filteredData].sort((a, b) => {
      const valA = a[sortKey];
      const valB = b[sortKey];
      if (valA === valB) return 0;
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (typeof valA === "number" && typeof valB === "number") {
        return sortOrder === "asc" ? valA - valB : valB - valA;
      }
      const strA = String(valA).toLowerCase();
      const strB = String(valB).toLowerCase();
      return sortOrder === "asc"
        ? strA.localeCompare(strB)
        : strB.localeCompare(strA);
    });
  }, [filteredData, sortKey, sortOrder]);

  // Pagination
  const totalPages = Math.ceil(sortedData.length / pageSize) || 1;
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortOrder("asc");
    }
  };

  const exportCsv = () => {
    if (!data || data.length === 0) return;
    const headerRow = resolvedColumns.map((col) => `"${col.header}"`).join(",");
    const rows = sortedData.map((row) =>
      resolvedColumns
        .map((col) => {
          const val = row[col.key];
          if (val === null || val === undefined) return '""';
          return `"${String(val).replace(/"/g, '""')}"`;
        })
        .join(",")
    );
    const csvContent = [headerRow, ...rows].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="card-glass p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-[17px] font-bold text-[#19222D] tracking-[-0.45px] m-0">
              {title}
            </h3>
            {badge && (
              <span className="text-[11px] font-bold text-[#7D8896] px-2 py-0.5 border border-[#E7EBF0] rounded-[6px] bg-[#FAFBFC]">
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[12px] text-[#86919E] mt-1 m-0">{subtitle}</p>
          )}
        </div>

        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9AA5B0]"
            />
            <input
              type="text"
              placeholder="Search records..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="h-[34px] pl-8 pr-3 text-[12px] bg-[#F8F9FB] border border-[#E2E7EE] rounded-lg focus:outline-none focus:border-[#4278B9] w-[180px] sm:w-[220px]"
            />
          </div>

          <button
            type="button"
            onClick={exportCsv}
            className="h-[34px] px-3 bg-white border border-[#E2E7EE] hover:bg-[#F9FBFD] rounded-lg text-[12px] font-semibold text-[#435166] inline-flex items-center gap-1.5 transition-colors"
            title="Download CSV"
          >
            <Download size={13} />
            <span className="hidden sm:inline">CSV</span>
          </button>
        </div>
      </div>

      <div className="overflow-x-auto border border-[#E7EBF0] rounded-lg">
        <table className="w-full border-collapse text-left text-[12px]">
          <thead>
            <tr className="bg-[#FAFBFC] border-b border-[#E7EBF0]">
              {resolvedColumns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                  className={`px-3.5 py-3 text-[10px] font-extrabold uppercase tracking-[0.85px] text-[#96A1AD] select-none ${
                    col.sortable !== false ? "cursor-pointer hover:text-[#19222D]" : ""
                  } ${col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left"}`}
                >
                  <div
                    className={`inline-flex items-center gap-1 ${
                      col.align === "right" ? "justify-end" : ""
                    }`}
                  >
                    <span>{col.header}</span>
                    {col.sortable !== false && (
                      <ArrowUpDown size={11} className="opacity-60" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F0F2F5]">
            {paginatedData.length === 0 ? (
              <tr>
                <td
                  colSpan={resolvedColumns.length}
                  className="px-4 py-8 text-center text-[#9AA5B0]"
                >
                  No records matching the filter criteria.
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className="hover:bg-[#FDFAF3] transition-colors duration-100"
                >
                  {resolvedColumns.map((col) => (
                    <td
                      key={col.key}
                      className={`px-3.5 py-3 text-[#465469] tabular-nums ${
                        col.align === "right"
                          ? "text-right font-medium"
                          : col.align === "center"
                          ? "text-center"
                          : "text-left"
                      } ${col.className || ""}`}
                    >
                      {col.accessor ? col.accessor(row) : String(row[col.key] ?? "—")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between text-[11px] text-[#86919E] mt-3">
        <div>
          Showing{" "}
          <span className="font-semibold text-[#19222D]">
            {sortedData.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}
          </span>{" "}
          to{" "}
          <span className="font-semibold text-[#19222D]">
            {Math.min(currentPage * pageSize, sortedData.length)}
          </span>{" "}
          of{" "}
          <span className="font-semibold text-[#19222D]">
            {sortedData.length.toLocaleString()}
          </span>{" "}
          rows
        </div>

        {totalPages > 1 && (
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-1.5 rounded border border-[#E2E7EE] disabled:opacity-40 hover:bg-[#F8F9FB]"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              type="button"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="p-1.5 rounded border border-[#E2E7EE] disabled:opacity-40 hover:bg-[#F8F9FB]"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
