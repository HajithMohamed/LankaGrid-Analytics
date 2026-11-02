import { NextRequest, NextResponse } from "next/server";
import { getAnalyticsData } from "@/lib/db/snapshot-loader";
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
    const result = await getAnalyticsData(upperId);
    return NextResponse.json(result, {
      status: result.success ? 200 : 500,
      headers: {
        "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
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
