import { NextRequest, NextResponse } from "next/server";

export function requireSession(req: NextRequest) {
  const session = req.cookies.get("session");
  if (!session?.value) {
    return NextResponse.json({ error: "未登录" }, { status: 401 });
  }
  return null;
}
