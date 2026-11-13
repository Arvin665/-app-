import { getDeviceId } from "./device";

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

function readableError(response) {
  const detail = response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("；");
  return `请求失败（${response?.statusCode || "网络异常"}）`;
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
      url: `${API_BASE_URL}${path}`,
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
      fail: (error) => reject(new ApiError(error.errMsg || "网络不可用", 0, error)),
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
      url: `${API_BASE_URL}${path}`,
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
      fail: (error) => reject(new ApiError(error.errMsg || "文件上传失败", 0, error)),
    });
  });
}

export async function transcribeAudio(blob) {
  const formData = new FormData();
  formData.append("file", blob, `dictation-${Date.now()}.wav`);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/ai/transcribe`, {
      method: "POST",
      headers: { "X-Device-ID": getDeviceId() },
      body: formData,
      signal: controller.signal,
    });
  } catch (error) {
    const message = error?.name === "AbortError" ? "语音识别超时，请重试" : "录音上传失败，请检查网络后重试";
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

export function download(path) {
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: `${API_BASE_URL}${path}`,
      header: { "X-Device-ID": getDeviceId() },
      success: (response) => {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.tempFilePath);
        } else {
          reject(new ApiError(`导出失败（${response.statusCode}）`, response.statusCode));
        }
      },
      fail: (error) => reject(new ApiError(error.errMsg || "下载失败", 0, error)),
    });
  });
}

export function isNetworkError(error) {
  return error?.status === 0 || /network|timeout|fail|offline/i.test(error?.message || "");
}
