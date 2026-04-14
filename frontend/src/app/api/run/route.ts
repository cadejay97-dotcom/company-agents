import { NextRequest, NextResponse } from "next/server";
import { requireSession } from "@/lib/session";

const BACKEND_URL = process.env.BACKEND_URL || "";
const APP_PASSWORD = process.env.APP_PASSWORD || "";

export async function POST(req: NextRequest) {
  const unauthorized = requireSession(req);
  if (unauthorized) return unauthorized;

  if (!BACKEND_URL) {
    return NextResponse.json({ error: "BACKEND_URL 未配置" }, { status: 500 });
  }

  const body = await req.json();
  const credentials = Buffer.from(`admin:${APP_PASSWORD}`).toString("base64");
  const response = await fetch(`${BACKEND_URL}/api/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Basic ${credentials}`,
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
