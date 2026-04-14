import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { password } = await req.json();
  const appPassword = process.env.APP_PASSWORD || "";

  if (!appPassword || password !== appPassword) {
    return NextResponse.json({ error: "密码错误" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set("session", "authenticated", {
    httpOnly: true,
    path: "/",
    sameSite: "strict",
    maxAge: 60 * 60 * 24 * 30,
  });
  return response;
}
