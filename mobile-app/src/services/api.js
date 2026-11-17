import { getDeviceId } from "./device";

const API_BASE_STORAGE_KEY = "asset-library-api-base-url";
const configuredApiBaseUrl = String(import.meta.env.VITE_API_BASE_URL || "").trim();
let platformApiBaseUrl = "http://127.0.0.1:8000/api/v1";
// #ifdef H5
platformApiBaseUrl = "/api/v1";
// #endif
const DEFAULT_API_BASE_URL = (configuredApiBaseUrl || platformApiBaseUrl).replace(/\/$/, "");

function normalizeApiBaseUrl(value) {
  let normalized = String(value || "").trim();
  if (!normalized) return DEFAULT_API_BASE_URL;
  if (normalized.startsWith("/")) {
    normalized = normalized.replace(/\/+$/, "") || "/";
    if (/\/api$/i.test(normalized)) normalized = `${normalized}/v1`;
    else if (!/\/api\/v1$/i.test(normalized)) {
      normalized = `${normalized === "/" ? "" : normalized}/api/v1`;
    }
    return normalized;
  }
  if (!/^https?:\/\//i.test(normalized)) normalized = `http://${normalized}`;
  normalized = normalized.replace(/\/+$/, "");
  if (/\/api$/i.test(normalized)) normalized = `${normalized}/v1`;
  else if (!/\/api\/v1$/i.test(normalized)) normalized = `${normalized}/api/v1`;
  return normalized;
}

function storedApiBaseUrl() {
  try {
    return uni.getStorageSync(API_BASE_STORAGE_KEY) || "";
  } catch (error) {
    return "";
  }
}

export let API_BASE_URL = normalizeApiBaseUrl(storedApiBaseUrl() || DEFAULT_API_BASE_URL);

export function setApiBaseUrl(value) {
  const normalized = normalizeApiBaseUrl(value);
  API_BASE_URL = normalized;
  try {
    uni.setStorageSync(API_BASE_STORAGE_KEY, normalized);
  } catch (error) {
    // 浏览器隐私模式可能禁用持久存储，本次运行仍使用当前地址。
  }
  return normalized;
}

export function resetApiBaseUrl() {
  API_BASE_URL = normalizeApiBaseUrl(DEFAULT_API_BASE_URL);
  try {
    uni.removeStorageSync(API_BASE_STORAGE_KEY);
  } catch (error) {
    // 地址重置不依赖持久存储是否可用。
  }
  return API_BASE_URL;
}

export function serviceRootUrl() {
  return API_BASE_URL.replace(/\/api\/v1\/?$/, "");
}

export function apiUrl(path = "") {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  if (/^https?:\/\//i.test(API_BASE_URL)) return `${API_BASE_URL}${suffix}`;
  if (API_BASE_URL.startsWith("/")) {
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    return `${origin}${API_BASE_URL}${suffix}`;
  }
  return `${API_BASE_URL}${suffix}`;
}

function readableError(response) {
  const detail = response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("；");
  return `资料库服务返回异常（${response?.statusCode || "未知状态"}）`;
}

function readableNetworkError(error) {
  const detail = String(error?.errMsg || error?.message || error || "").trim();
  if (/timeout|超时/i.test(detail)) {
    return `连接资料库服务超时。当前地址：${API_BASE_URL}`;
  }
  if (/abort|取消/i.test(detail)) {
    return "请求已取消";
  }
  return `无法连接资料库服务。当前地址：${API_BASE_URL}。请确认后台已启动、手机可访问该地址，并检查网络。`;
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export function request(path, options = {}) {
  const deviceId = getDeviceId();
  return new Promise((resolve, reject) => {
    uni.request({
      url: apiUrl(path),
      method: options.method || "GET",
      data: options.data,
      timeout: options.timeout || 20000,
      header: {
        "Content-Type": "application/json",
        "X-Device-ID": deviceId,
        ...(options.header || {}),
      },
      success: (response) => {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data);
          return;
        }
        reject(new ApiError(readableError(response), response.statusCode, response.data));
      },
      fail: (error) => reject(new ApiError(readableNetworkError(error), 0, error)),
    });
  });
}

export function probeService(timeout = 8000) {
  return new Promise((resolve) => {
    uni.request({
      url: apiUrl("/health"),
      method: "GET",
      timeout,
      success: (response) => {
        const healthy = response.statusCode >= 200
          && response.statusCode < 300
          && response.data?.status === "ok";
        resolve({
          ok: healthy,
          statusCode: response.statusCode,
          data: response.data || null,
          baseUrl: API_BASE_URL,
          message: healthy ? "服务连接正常" : readableError(response),
        });
      },
      fail: (error) => resolve({
        ok: false,
        statusCode: 0,
        data: null,
        baseUrl: API_BASE_URL,
        message: readableNetworkError(error),
      }),
    });
  });
}

export function postForm(path, fields) {
  const body = Object.entries(fields)
    .filter(([, value]) => value !== undefined && value !== null)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join("&");
  return request(path, {
    method: "POST",
    data: body,
    header: { "Content-Type": "application/x-www-form-urlencoded" },
  });
}

export function upload(path, filePath, formData = {}) {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: apiUrl(path),
      filePath,
      name: "file",
      formData,
      header: { "X-Device-ID": getDeviceId() },
      timeout: 300000,
      success: (response) => {
        let data = response.data;
        try {
          data = JSON.parse(data);
        } catch (error) {
          // 文件接口正常返回 JSON；保留原始字符串用于错误提示。
        }
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(data);
          return;
        }
        reject(new ApiError(readableError({ statusCode: response.statusCode, data }), response.statusCode, data));
      },
      fail: (error) => reject(new ApiError(readableNetworkError(error), 0, error)),
    });
  });
}

export async function uploadBlob(path, blob, formData = {}, fileName = "file") {
  const body = new FormData();
  body.append("file", blob, fileName);
  Object.entries(formData || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) body.append(key, String(value));
  });
  let response;
  try {
    response = await fetch(apiUrl(path), {
      method: "POST",
      headers: { "X-Device-ID": getDeviceId() },
      body,
    });
  } catch (error) {
    throw new ApiError(readableNetworkError(error), 0, error);
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(readableError({ statusCode: response.status, data }), response.status, data);
  }
  return data;
}

export async function transcribeAudio(blob) {
  const formData = new FormData();
  formData.append("file", blob, `dictation-${Date.now()}.wav`);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  let response;
  try {
    response = await fetch(apiUrl("/ai/transcribe"), {
      method: "POST",
      headers: { "X-Device-ID": getDeviceId() },
      body: formData,
      signal: controller.signal,
    });
  } catch (error) {
    const message = error?.name === "AbortError"
      ? "语音识别超时，请缩短录音后重试"
      : readableNetworkError(error);
    throw new ApiError(message, 0, error);
  } finally {
    clearTimeout(timer);
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(readableError({ statusCode: response.status, data }), response.status, data);
  }
  return data;
}

export function transcribeFile(filePath) {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: apiUrl("/ai/transcribe-media"),
      filePath,
      name: "file",
      header: { "X-Device-ID": getDeviceId() },
      timeout: 130000,
      success: (response) => {
        let data = response.data;
        try {
          data = JSON.parse(data);
        } catch (error) {
          data = {};
        }
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(data);
          return;
        }
        reject(new ApiError(
          readableError({ statusCode: response.statusCode, data }),
          response.statusCode,
          data,
        ));
      },
      fail: (error) => reject(new ApiError(readableNetworkError(error), 0, error)),
    });
  });
}

export function download(path) {
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: apiUrl(path),
      header: { "X-Device-ID": getDeviceId() },
      success: (response) => {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.tempFilePath);
        } else {
          reject(new ApiError(`导出失败（${response.statusCode}）`, response.statusCode));
        }
      },
      fail: (error) => reject(new ApiError(readableNetworkError(error), 0, error)),
    });
  });
}

export function isNetworkError(error) {
  return error?.status === 0 || /network|timeout|无法连接|offline/i.test(error?.message || "");
}
