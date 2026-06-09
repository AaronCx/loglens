import { NextRequest } from "next/server";

// Server-side proxy to the LogLens backend. Replaces the next.config rewrite
// so the API key stays on the server (LOGLENS_API_KEY) and is never shipped
// to the browser.
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function proxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await params;
  const url = `${BACKEND_URL}/${path.join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  // A key explicitly supplied by the client (e.g. the delete prompt) wins;
  // otherwise attach the server-only key for dashboard reads.
  const apiKey = req.headers.get("x-api-key") || process.env.LOGLENS_API_KEY;
  if (apiKey) headers.set("x-api-key", apiKey);

  const res = await fetch(url, {
    method: req.method,
    headers,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
    cache: "no-store",
  });

  return new Response(res.body, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") ?? "application/json",
    },
  });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
