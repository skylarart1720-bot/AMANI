import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
const allowed = new Set([
  "support/status",
  "support/staff",
  "support/directory",
  "support/sessions",
  "support/messages",
  "support/events",
  "support/chat",
  "support/handoff",
  "support/check-link",
  "support/translate",
  "support/languages",
]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const path = (await context.params).path.join("/");
  if (!allowed.has(path) && !/^support\/languages\/[a-zA-Z-]+$/.test(path))
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
    // Next's internal URL can use localhost while the browser uses 127.0.0.1.
    // The actual Host header is the browser-facing authority; forwarded hosts are not trusted.
    if (origin) {
      try {
        const parsed = new URL(origin);
        if (
          !["http:", "https:"].includes(parsed.protocol) ||
          parsed.host !== request.headers.get("host")
        )
          return NextResponse.json(
            { detail: "Invalid origin" },
            { status: 403 },
          );
      } catch {
        return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
      }
    }
  }
  try {
    const body = request.method === "GET" ? undefined : await request.text();
    if (body && body.length > 16000)
      return NextResponse.json(
        { detail: "Request too large" },
        { status: 413 },
      );
    // Filtered routes such as support/directory accept query parameters, so the
    // search string must be carried upstream instead of being dropped here.
    const upstream = `${process.env.ORCHESTRATOR_URL || "http://127.0.0.1:8000"}/${path}${request.nextUrl.search}`;
    const response = await fetch(upstream, {
      method: request.method,
      body: body || undefined,
      headers: {
        "Content-Type": "application/json",
        Authorization: request.headers.get("authorization") || "",
      },
      cache: "no-store",
      signal:
        path === "support/events"
          ? request.signal
          : AbortSignal.timeout(35000),
    });
    if (response.headers.get("content-type")?.includes("text/event-stream"))
      return new NextResponse(response.body, {
        status: response.status,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-store",
          "X-Accel-Buffering": "no",
        },
      });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail: "The support service is unavailable. Please try again shortly.",
      },
      { status: 503 },
    );
  }
}
export { proxy as GET, proxy as POST, proxy as DELETE };
