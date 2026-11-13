// H5 使用持久随机 UUID，原生端严格优先读取 iOS IDFV / Android ID。
const DEVICE_KEY = "asset-library-device-id";

function randomHex() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

function normalizePlatformId(raw) {
  const value = String(raw || "").trim().toLowerCase().replace(/-/g, "");
  if (/^[a-f0-9]{32}$/.test(value)) return value;
  // Android ID 原生为 16 位十六进制，固定复写为 32 位以满足数据库长度，同时保留可辨识来源。
  if (/^[a-f0-9]{16}$/.test(value)) return `${value}${value}`;
  return "";
}

function iosIdfv() {
  // #ifdef APP-PLUS
  if (plus.os.name === "iOS") {
    try {
      const UIDevice = plus.ios.importClass("UIDevice");
      const identifier = UIDevice.currentDevice().identifierForVendor().UUIDString();
      return normalizePlatformId(identifier);
    } catch (error) {
      console.warn("读取 iOS IDFV 失败", error);
    }
  }
  // #endif
  return "";
}

function androidId() {
  // #ifdef APP-PLUS
  if (plus.os.name === "Android") {
    try {
      const Secure = plus.android.importClass("android.provider.Settings$Secure");
      const main = plus.android.runtimeMainActivity();
      const identifier = Secure.getString(main.getContentResolver(), "android_id");
      return normalizePlatformId(identifier);
    } catch (error) {
      console.warn("读取 Android ID 失败", error);
    }
  }
  // #endif
  return "";
}

function appDeviceId() {
  // IDFV 与 Android ID 是需求指定的主标识；仅在平台桥接失败时退回系统 UUID。
  const strictId = plus.os.name === "iOS" ? iosIdfv() : androidId();
  if (strictId) return strictId;
  // #ifdef APP-PLUS
  try {
    const fallback = normalizePlatformId(plus.device.uuid);
    if (fallback) return fallback;
  } catch (error) {
    console.warn("读取系统设备 UUID 失败", error);
  }
  // #endif
  return randomHex();
}

export function getDeviceId() {
  let deviceId = uni.getStorageSync(DEVICE_KEY);
  if (!/^[a-f0-9]{32}$/.test(deviceId || "")) {
    // #ifdef APP-PLUS
    deviceId = appDeviceId();
    // #endif
    // #ifndef APP-PLUS
    deviceId = randomHex();
    // #endif
    uni.setStorageSync(DEVICE_KEY, deviceId);
  }
  return deviceId;
}

export function deviceName() {
  const system = uni.getSystemInfoSync();
  return `${system.brand || system.platform || "设备"}-${system.model || "商办资产库"}`.slice(0, 100);
}
