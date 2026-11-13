const DEVICE_KEY = "asset-library-desktop-device-id";
const SESSION_KEY = "asset-library-desktop-session";

export function randomHex(length = 32) {
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    const bytes = new Uint8Array(length / 2);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  }
  return Array.from({ length }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

export function setDeviceInfo(info = {}) {
  if (info.deviceId && /^[a-f0-9]{32}$/i.test(info.deviceId)) {
    localStorage.setItem(DEVICE_KEY, info.deviceId.toLowerCase());
  }
  if (info.deviceName) localStorage.setItem("asset-library-desktop-device-name", info.deviceName);
}

export function getDeviceId() {
  let value = localStorage.getItem(DEVICE_KEY);
  if (!/^[a-f0-9]{32}$/i.test(value || "")) {
    value = randomHex();
    localStorage.setItem(DEVICE_KEY, value);
  }
  return value.toLowerCase();
}

export function getDeviceName() {
  return localStorage.getItem("asset-library-desktop-device-name") || "Windows 工作台";
}

export function getSession() {
  return JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
}

export function saveSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}
