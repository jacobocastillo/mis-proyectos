import { isAccessTokenValid } from "@/services/auth/session";

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);
const AUTH_PAGES = new Set(["/login", "/register"]);

function isProtectedPath(pathname: string): boolean {
  if (pathname === "/") {
    return true;
  }

  return ["/habits", "/stats", "/profile", "/pomodoro"].some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function isOfflineBuildMode(rawValue = process.env.NEXT_PUBLIC_OFFLINE_MODE): boolean {
  return TRUE_VALUES.has((rawValue ?? "").trim().toLowerCase());
}

export function getAuthRedirectTarget(pathname: string, search: string): string {
  return pathname === "/" ? "/" : `${pathname}${search}`;
}

export type RequestAuthDecision =
  | { kind: "allow" }
  | { kind: "redirect_to_login"; nextPath: string }
  | { kind: "redirect_to_home" };

export function resolveRequestAuthDecision(params: {
  pathname: string;
  search: string;
  accessToken?: string | null;
  offlineMode?: boolean;
}): RequestAuthDecision {
  if (params.offlineMode ?? isOfflineBuildMode()) {
    return { kind: "allow" };
  }

  const token = params.accessToken ?? "";
  const hasValidSession = token.length > 0 && isAccessTokenValid(token);

  if (isProtectedPath(params.pathname) && !hasValidSession) {
    return {
      kind: "redirect_to_login",
      nextPath: getAuthRedirectTarget(params.pathname, params.search),
    };
  }

  if (AUTH_PAGES.has(params.pathname) && hasValidSession) {
    return { kind: "redirect_to_home" };
  }

  return { kind: "allow" };
}
