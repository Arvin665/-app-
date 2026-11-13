import { getDeviceId } from "./device";

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export function isNetworkError(error) {
  return error?.name === "TypeError" || error?.status === 0 || /network|fetch|timed? ?out|failed/i.test(error?.message || "");
}

function readableDetail(detail) {
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("；");
  return "";
}

export async function apiRequest(path, options = {}) {
  const headers = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    "X-Device-ID": getDeviceId(),
    ...(options.headers || {}),
  };
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
    if (options.responseType === "blob") {
      if (!response.ok) throw new ApiError(`请求失败（${response.status}）`, response.status);
      return response.blob();
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new ApiError(readableDetail(data.detail) || `请求失败（${response.status}）`, response.status, data);
    }
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(error.message || "网络不可用，请检查后端服务", 0, error);
  }
}

export function api(path, options = {}) {
  return apiRequest(path, {
    ...options,
    body: options.data === undefined ? options.body : JSON.stringify(options.data),
  });
}

export function uploadFile(path, file, fields = {}) {
  const form = new FormData();
  form.append("file", file);
  Object.entries(fields).forEach(([key, value]) => form.append(key, value));
  return apiRequest(path, { method: "POST", body: form });
}

export async function downloadFile(path, fallbackName) {
  const blob = await apiRequest(path, { responseType: "blob" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
