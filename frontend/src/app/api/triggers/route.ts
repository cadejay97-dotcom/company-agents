import { NextRequest, NextResponse } from "next/server";
import { requireSession } from "@/lib/session";

const BACKEND_URL = process.env.BACKEND_URL || "";
const APP_PASSWORD = process.env.APP_PASSWORD || "";

export async function GET(req: NextRequest) {
  const unauthorized = requireSession(req);
  if (unauthorized) return unauthorized;

  if (!BACKEND_URL) {
    return NextResponse.json({ error: "BACKEND_URL 未配置" }, { status: 500 });
  }

  const credentials = Buffer.from(`admin:${APP_PASSWORD}`).toString("base64");
  const response = await fetch(`${BACKEND_URL}/api/triggers`, {
    headers: {
      Authorization: `Basic ${credentials}`,
    },
    cache: "no-store",
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
