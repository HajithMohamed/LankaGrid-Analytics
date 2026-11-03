import { NextRequest, NextResponse } from "next/server";
import { getAnalyticsData, loadCsvSnapshot } from "@/lib/db/snapshot-loader";
import { QUERY_REGISTRY } from "@/lib/analytics/query-registry";

/**
 * Helper to convert array of records into RFC 4180 compliant CSV string
 */
function recordsToCsv(records: Record<string, unknown>[]): string {
  if (!records || records.length === 0) return "";
  const headers = Object.keys(records[0]);
  const escapeCsv = (val: unknown): string => {
    if (val === null || val === undefined) return "";
    const str = String(val);
    if (str.includes(",") || str.includes('"') || str.includes("\n") || str.includes("\r")) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const headerLine = headers.map(escapeCsv).join(",");
  const rowLines = records.map((record) => headers.map((h) => escapeCsv(record[h])).join(","));
  return [headerLine, ...rowLines].join("\n");
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ queryId: string }> }
) {
  const { queryId } = await params;
  const upperId = queryId.toUpperCase();

  // Strict allowlisting
  if (!QUERY_REGISTRY[upperId]) {
    return NextResponse.json(
      {
        success: false,
        error: `Query identifier '${queryId}' is not authorized. Must be Q01 through Q24.`,
      },
      { status: 404 }
    );
  }

  try {
    const searchParams = request.nextUrl.searchParams;
    const filterKey = searchParams.get("filterKey");
    const filterValue = searchParams.get("filterValue");

    // Fetch analytical data (live PostgreSQL or snapshot fallback)
    const result = await getAnalyticsData(upperId);

    if (result.success && Array.isArray(result.data) && result.data.length > 0) {
      let filteredData = result.data;

      // Apply dynamic column filter if specified
      if (filterKey && filterValue && filterValue !== "all") {
        filteredData = filteredData.filter((row) => {
          const val = String(row[filterKey] || "").toLowerCase();
          return val.includes(filterValue.toLowerCase());
        });
      }

      const csvContent = recordsToCsv(filteredData);
      return new NextResponse(csvContent, {
        status: 200,
        headers: {
          "Content-Type": "text/csv; charset=utf-8",
          "Content-Disposition": `attachment; filename="gridlens-${upperId}-${result.sourceMode}.csv"`,
          "X-GridLens-Source": result.sourceMode,
        },
      });
    }

    // Fall back to pre-rendered static snapshot CSV
    const csvContent = await loadCsvSnapshot(upperId);
    return new NextResponse(csvContent, {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="gridlens-${upperId}-snapshot.csv"`,
        "X-GridLens-Source": "snapshot",
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        queryId: upperId,
        error: "Failed to export query dataset.",
      },
      { status: 500 }
    );
  }
}
