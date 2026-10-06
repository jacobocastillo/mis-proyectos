import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { resolveRequestAuthDecision } from "@/services/auth/requestProtection";
import { AUTH_COOKIE_NAME } from "@/services/auth/session";

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value ?? "";
  const decision = resolveRequestAuthDecision({
    pathname,
    search,
    accessToken: token,
  });

  if (decision.kind === "redirect_to_login") {
    const loginUrl = new URL("/login", request.url);

    if (decision.nextPath !== "/") {
      loginUrl.searchParams.set("next", decision.nextPath);
    }

    return NextResponse.redirect(loginUrl);
  }

  if (decision.kind === "redirect_to_home") {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/habits/:path*", "/stats/:path*", "/profile/:path*", "/pomodoro/:path*", "/login", "/register"],
};
