import { ApiError, request } from "./api";
import { deviceName, getDeviceId } from "./device";

const SESSION_KEY = "asset-library-session";

export function getSession() {
  return uni.getStorageSync(SESSION_KEY) || null;
}

export function saveSession(session) {
  uni.setStorageSync(SESSION_KEY, session);
  return session;
}

export async function bindDevice(inviteCode) {
  const data = await request("/auth/bind", {
    method: "POST",
    data: { invite_code: inviteCode.trim(), device_id: getDeviceId(), device_name: deviceName() },
  });
  return saveSession(data);
}

export async function checkBinding() {
  const session = getSession();
  if (!session?.device_id) return null;
  try {
    const fresh = await request("/auth/me");
    return saveSession(fresh);
  } catch (error) {
    if (error instanceof ApiError && [401, 403].includes(error.status)) return null;
    // 断网时保留本地身份，桌面端/移动端都可以继续使用缓存数据。
    return session;
  }
}

export function ensureBound() {
  if (getSession()) return true;
  uni.reLaunch({ url: "/pages/bind/index" });
  return false;
}

export async function heartbeat() {
  try {
    const result = await request("/auth/heartbeat", { method: "POST" });
    const session = getSession();
    if (session) saveSession({ ...session, last_online_time: result.server_time, role_level: result.role_level });
    return result;
  } catch (error) {
    return null;
  }
}
