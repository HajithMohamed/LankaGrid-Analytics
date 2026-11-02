import { NextRequest, NextResponse } from "next/server";
import { loadCsvSnapshot } from "@/lib/db/snapshot-loader";
import { QUERY_REGISTRY } from "@/lib/analytics/query-registry";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ queryId: string }> }
) {
  const { queryId } = await params;
  const upperId = queryId.toUpperCase();

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
    const csvContent = await loadCsvSnapshot(upperId);
    return new NextResponse(csvContent, {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="gridlens-${upperId}.csv"`,
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        queryId: upperId,
        error: (error as Error).message,
      },
      { status: 500 }
    );
  }
}
