import { spawnSync } from "node:child_process";

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);
const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

function isOfflineModeEnabled(rawValue) {
  return TRUE_VALUES.has((rawValue ?? "").trim().toLowerCase());
}

function validateApiUrl(rawValue) {
  const value = (rawValue ?? "").trim();

  if (!value) {
    throw new Error(
      "Set NEXT_PUBLIC_API_URL to an https:// backend URL, or set NEXT_PUBLIC_OFFLINE_MODE=true for offline mobile builds.",
    );
  }

  let url;

  try {
    url = new URL(value);
  } catch {
    throw new Error(
      "NEXT_PUBLIC_API_URL must be an absolute https:// URL for connected mobile builds.",
    );
  }

  if (url.protocol !== "https:") {
    throw new Error(
      "NEXT_PUBLIC_API_URL must use https:// for connected mobile builds. Use NEXT_PUBLIC_OFFLINE_MODE=true when backend is unavailable.",
    );
  }

  if (LOOPBACK_HOSTS.has(url.hostname.toLowerCase())) {
    throw new Error(
      "NEXT_PUBLIC_API_URL cannot use localhost for mobile builds. Use a reachable hosted URL, or set NEXT_PUBLIC_OFFLINE_MODE=true.",
    );
  }
}

if (!isOfflineModeEnabled(process.env.NEXT_PUBLIC_OFFLINE_MODE)) {
  validateApiUrl(process.env.NEXT_PUBLIC_API_URL);
}

const env = {
  ...process.env,
  NEXT_BUILD_TARGET: "mobile",
};

const nextBinary = process.platform === "win32" ? "next.cmd" : "next";
const result = spawnSync(nextBinary, ["build"], {
  env,
  stdio: "inherit",
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
