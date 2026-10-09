import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
export const dynamic = "force-dynamic";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const path = (await context.params).path.join("/");
  const jar = await cookies();
  const base = process.env.ORCHESTRATOR_URL || "http://127.0.0.1:8000";
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
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
  if (path === "logout") {
    jar.delete("amani-admin");
    return NextResponse.json({ ok: true });
  }
  try {
    if (path === "login" && request.method === "POST") {
      const payload = await request.json();
      const token = typeof payload.token === "string" ? payload.token.trim() : payload.token;
      if (typeof token !== "string" || token.length < 20 || token.length > 200)
        return NextResponse.json(
          { detail: "Invalid access token" },
          { status: 401 },
        );
      const result = await fetch(`${base}/admin/queue`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });
      if (!result.ok)
        return NextResponse.json(
          { detail: result.status === 401 || result.status === 403
            ? "Access token not recognised. Enter the current moderator token, without quotes or the filename."
            : "The support service is temporarily unavailable. Please retry." },
          { status: result.status === 401 || result.status === 403 ? 401 : 503 },
        );
      jar.set("amani-admin", token, {
        httpOnly: true,
        secure: process.env.COOKIE_SECURE === 'true' || request.nextUrl.protocol === "https:" || request.headers.get('x-forwarded-proto') === 'https',
        sameSite: "strict",
        path: "/",
        maxAge: 3600,
      });
      return NextResponse.json({ ok: true });
    }
    if (
      !/^admin\/(events|queue(?:\/[A-Z0-9-]+(?:\/reply)?)?|directory|knowledge(?:\/[a-f0-9]+)?|audit)$/.test(
        path,
      )
    )
      return NextResponse.json({ detail: "Not found" }, { status: 404 });
    const token = jar.get("amani-admin")?.value;
    if (!token)
      return NextResponse.json(
        { detail: "Sign in to continue" },
        { status: 401 },
      );
    const body = request.method === "GET" ? undefined : await request.text();
    if (body && body.length > 16000)
      return NextResponse.json(
        { detail: "Request too large" },
        { status: 413 },
      );
    // admin/audit is filtered by staff id and action, so carry the search upstream.
    const result = await fetch(`${base}/${path}${request.nextUrl.search}`, {
      method: request.method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body,
      cache: "no-store",
      signal:
        path === "admin/events" ? request.signal : AbortSignal.timeout(10000),
    });
    if (result.headers.get("content-type")?.includes("text/event-stream"))
      return new NextResponse(result.body, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-store",
          "X-Accel-Buffering": "no",
        },
      });
    return new NextResponse(await result.text(), {
      status: result.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "The support API could not be reached" },
      { status: 503 },
    );
  }
}
export { proxy as GET, proxy as POST, proxy as PATCH, proxy as PUT };
