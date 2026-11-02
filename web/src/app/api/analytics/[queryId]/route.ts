import { NextRequest, NextResponse } from "next/server";
import { getAnalyticsData } from "@/lib/db/snapshot-loader";
import { QUERY_REGISTRY } from "@/lib/analytics/query-registry";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ queryId: string }> }
) {
  const { queryId } = await params;
  const upperId = queryId.toUpperCase();

  // Strict allowlist validation: Only Q01 through Q24 are permitted
  if (!QUERY_REGISTRY[upperId]) {
    return NextResponse.json(
      {
        success: false,
        error: `Query identifier '${queryId}' is not authorized. Permitted queries are strictly Q01 through Q24.`,
      },
      { status: 404 }
    );
  }

  try {
    const result = await getAnalyticsData(upperId);

    // Optional safe pagination
    const searchParams = request.nextUrl.searchParams;
    const pageParam = searchParams.get("page");
    const limitParam = searchParams.get("limit");

    if (pageParam && limitParam && result.success && Array.isArray(result.data)) {
      const page = Math.max(1, parseInt(pageParam, 10) || 1);
      const limit = Math.min(500, Math.max(1, parseInt(limitParam, 10) || 50));
      const totalRows = result.data.length;
      const startIndex = (page - 1) * limit;
      const paginatedData = result.data.slice(startIndex, startIndex + limit);

      return NextResponse.json(
        {
          ...result,
          data: paginatedData,
          pagination: {
            page,
            limit,
            totalRows,
            totalPages: Math.ceil(totalRows / limit),
          },
        },
        {
          status: 200,
          headers: {
            "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
          },
        }
      );
    }

    return NextResponse.json(result, {
      status: result.success ? 200 : 500,
      headers: {
        "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
      },
    });
  } catch (error) {
    // Sanitize error response: never leak internal stack traces or connection strings
    console.error(`Internal error processing analytics query ${upperId}:`, error);
    return NextResponse.json(
      {
        success: false,
        queryId: upperId,
        error: "An internal error occurred while processing the analytical query. Please verify warehouse connectivity.",
      },
      { status: 500 }
    );
  }
}
