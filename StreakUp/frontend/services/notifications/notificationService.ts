import { Capacitor } from "@capacitor/core";
import { PushNotifications } from "@capacitor/push-notifications";
import type { Token, PushNotificationSchema } from "@capacitor/push-notifications";
import { API_ENDPOINTS } from "@/services/api/endpoints";
import { getSession } from "@/services/auth/authService";

export type PushPermissionState = "granted" | "denied" | "prompt" | "unavailable";

function isNative(): boolean {
  return Capacitor.isNativePlatform();
}

function getAuthHeader(): HeadersInit {
  const session = getSession();
  return session?.accessToken
    ? { Authorization: `Bearer ${session.accessToken}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

async function postDeviceToken(token: string): Promise<void> {
  await fetch(API_ENDPOINTS.user.deviceToken, {
    method: "POST",
    headers: getAuthHeader(),
    body: JSON.stringify({ fcm_token: token }),
  });
}

export async function requestPushPermission(): Promise<PushPermissionState> {
  if (!isNative()) return "unavailable";

  const current = await PushNotifications.checkPermissions();
  if (current.receive === "granted") return "granted";

  const result = await PushNotifications.requestPermissions();
  return result.receive === "granted" ? "granted" : "denied";
}

export async function registerForPush(): Promise<void> {
  if (!isNative()) return;

  const permission = await requestPushPermission();
  if (permission !== "granted") return;

  await PushNotifications.register();

  PushNotifications.addListener("registration", (token: Token) => {
    void postDeviceToken(token.value);
  });
}

export function onNotificationReceived(
  callback: (notification: PushNotificationSchema) => void
): () => void {
  if (!isNative()) return () => undefined;

  const listener = PushNotifications.addListener("pushNotificationReceived", callback);
  return () => void listener.then((l) => l.remove());
}
