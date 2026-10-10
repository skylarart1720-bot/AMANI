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
  if (request.method === "GET" && /^support\/languages(?:\/[a-zA-Z-]+)?$/.test(path)) {
    try {
      const result = await fetch(`${base}/${path}`, {cache: "no-store", signal: AbortSignal.timeout(10000)});
      return NextResponse.json(await result.json(), {status: result.status});
    } catch {
      return NextResponse.json({detail: "Translations are unavailable."}, {status: 503});
    }
  }
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
    const token = jar.get("amani-admin")?.value;
    if (token) {
      try {
        await fetch(`${base}/admin/logout`, {
          method: "POST", headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.timeout(10000), cache: "no-store",
        });
      } catch {
        jar.delete("amani-admin");
        return NextResponse.json({ detail: "Signed out in this browser. The service could not revoke the session; it expires within one hour." }, { status: 503 });
      }
    }
    jar.delete("amani-admin");
    return NextResponse.json({ ok: true });
  }
  try {
    if (path === "login" && request.method === "POST") {
      const payload = await request.json();
      if (!["staff", "super_admin"].includes(payload.mode))
        return NextResponse.json(
          { detail: "Choose Staff or Super Admin." },
          { status: 422 },
        );
      const result = await fetch(`${base}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: payload.mode, token: payload.token || "", staff_id: payload.staff_id || "", password: payload.password || "" }),
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });
      if (!result.ok) return new NextResponse(await result.text(), { status: result.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
      const identity = await result.json();
      jar.set("amani-admin", identity.token, {
        httpOnly: true,
        secure: process.env.COOKIE_SECURE === 'true' || request.nextUrl.protocol === "https:" || request.headers.get('x-forwarded-proto') === 'https',
        sameSite: "strict",
        path: "/",
        maxAge: 3600,
      });
      return NextResponse.json({ ok: true, actor: identity.actor, role: identity.role });
    }
    if (
      !/^admin\/(me|presence|feedback|service-settings|activity|assignment-options|setup|languages\/[a-zA-Z-]+|staff(?:\/[a-z0-9._@-]+)?|events|queue(?:\/[A-Z0-9-]+(?:\/(?:reply|transfer|notes))?)?|directory|knowledge(?:\/[a-f0-9]+)?|audit)$/.test(
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
    // Pass the upstream status through: without it an upstream auth or rate-limit
    // failure on the event stream is reported to the browser as a healthy 200.
    if (result.headers.get("content-type")?.includes("text/event-stream"))
      return new NextResponse(result.body, {
        status: result.status,
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
