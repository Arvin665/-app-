import { API_BASE_URL, request, upload, uploadBlob } from "./api";
import { getDeviceId } from "./device";

export const materialTypeLabels = {
  image: "图片",
  pdf: "PDF",
  excel: "表格",
  csv: "CSV",
  word: "文档",
  presentation: "演示",
  text: "文本",
  audio: "音频",
  video: "视频",
  archive: "压缩包",
  other: "其他",
};

export const extractionLabels = {
  extracted: "已提取正文",
  stored: "原件已安全存放",
  unavailable: "原件已存，待配置识别",
  failed: "原件已存，提取失败",
};

export function formatFileSize(bytes) {
  const size = Number(bytes || 0);
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function formatMaterialDate(value) {
  if (!value) return "";
  return String(value).replace("T", " ").slice(0, 16);
}

function normalizeChosenFile(file, fallbackName = "资料文件") {
  const path = file.path || file.tempFilePath || file.url;
  if (!path) return null;
  return {
    path,
    name: file.name || path.split(/[\\/]/).pop() || fallbackName,
    size: Number(file.size || file.raw?.size || 0),
    type: file.type || file.raw?.type || "",
    raw: file,
  };
}

export function chooseImages({ count = 9, sourceType = ["album"] } = {}) {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count,
      sizeType: ["original"],
      sourceType,
      success: (result) => {
        const paths = result.tempFilePaths || [];
        resolve(
          paths
            .map((path, index) => normalizeChosenFile(result.tempFiles?.[index] || { path }, `图片${index + 1}`))
            .filter(Boolean),
        );
      },
      fail: (error) => {
        if (/cancel/i.test(error.errMsg || "")) resolve([]);
        else reject(error);
      },
    });
  });
}

function canUseBrowserFilePicker() {
  return typeof document !== "undefined" && typeof File !== "undefined";
}

function chooseBrowserFiles({ count = 9 } = {}) {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    let settled = false;
    const cleanup = () => {
      window.removeEventListener("focus", handleWindowFocus);
      input.remove();
    };
    const finish = (files) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(files);
    };
    const handleWindowFocus = () => {
      setTimeout(() => {
        if (!input.files?.length) finish([]);
      }, 700);
    };
    input.type = "file";
    input.multiple = count > 1;
    input.style.position = "fixed";
    input.style.left = "-9999px";
    input.style.width = "1px";
    input.style.height = "1px";
    input.addEventListener("change", () => {
      const files = Array.from(input.files || []).slice(0, count).map((file, index) => ({
        path: URL.createObjectURL(file),
        name: file.name || `资料${index + 1}`,
        size: file.size,
        type: file.type,
        file,
        raw: file,
      }));
      finish(files);
    });
    input.addEventListener("cancel", () => finish([]));
    document.body.appendChild(input);
    window.addEventListener("focus", handleWindowFocus, { once: true });
    input.click();
  });
}

export function chooseFiles({ count = 9 } = {}) {
  if (typeof uni.chooseFile !== "function" && canUseBrowserFilePicker()) {
    return chooseBrowserFiles({ count });
  }
  if (typeof uni.chooseFile !== "function") {
    return rejectUnsupported();
  }
  return new Promise((resolve, reject) => {
    uni.chooseFile({
      count,
      type: "all",
      success: (result) => {
        const paths = result.tempFilePaths || [];
        resolve(
          paths
            .map((path, index) => normalizeChosenFile(result.tempFiles?.[index] || { path }, `资料${index + 1}`))
            .filter(Boolean),
        );
      },
      fail: (error) => {
        if (/cancel/i.test(error.errMsg || "")) resolve([]);
        else reject(error);
      },
    });
  });
}

function rejectUnsupported() {
  const error = new Error("当前运行环境暂不支持系统文件选择，请使用 H5 或系统文件导入能力");
  uni.showToast({ title: error.message, icon: "none", duration: 2800 });
  return Promise.reject(error);
}

export function materialUploadForm({ module, recordId, title } = {}) {
  const form = { module };
  if (recordId) form.record_id = recordId;
  if (title) form.title = title;
  return form;
}

export async function uploadMaterial(file, { module, recordId, title } = {}) {
  const normalized = normalizeChosenFile(file);
  if (!normalized) throw new Error("没有可上传的文件");
  const blob = normalized.file instanceof Blob
    ? normalized.file
    : normalized.raw?.file instanceof Blob
      ? normalized.raw.file
      : normalized.raw instanceof Blob
        ? normalized.raw
        : null;
  if (blob) {
    return uploadBlob(
      "/materials/upload",
      blob,
      materialUploadForm({ module, recordId, title }),
      normalized.name,
    );
  }
  return upload("/materials/upload", normalized.path, materialUploadForm({ module, recordId, title }));
}

export function listMaterials({ module, fileType, keyword, recordId, page = 1, pageSize = 30 } = {}) {
  const params = new URLSearchParams();
  if (module) params.set("module", module);
  if (fileType) params.set("file_type", fileType);
  if (keyword) params.set("keyword", keyword);
  if (recordId) params.set("record_id", recordId);
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return request(`/materials?${params.toString()}`);
}

export function getMaterial(materialId) {
  return request(`/materials/${materialId}`);
}

export function linkMaterial(materialId, recordId) {
  return request(`/materials/${materialId}/link`, {
    method: "POST",
    data: { record_id: recordId },
  });
}

export function deleteMaterial(materialId) {
  return request(`/materials/${materialId}`, { method: "DELETE" });
}

export function openMaterial(material, { openExternally = false } = {}) {
  if (!material?.file_url) {
    return Promise.reject(new Error("这份资料没有可打开的原件地址。"));
  }
  if (material.file_type === "image" && !openExternally) {
    return new Promise((resolve, reject) => {
      uni.previewImage({
        urls: [material.file_url],
        current: material.file_url,
        success: () => resolve(true),
        fail: () => reject(new Error("图片预览没有打开，请重试。")),
      });
    });
  }

  // #ifdef H5
  try {
    const opened = window.open(material.file_url, "_blank", "noopener,noreferrer");
    if (!opened) throw new Error("浏览器拦截了新页面，请允许打开原件后重试。");
    return Promise.resolve(true);
  } catch (error) {
    return Promise.reject(error instanceof Error ? error : new Error("原件暂时无法打开。"));
  }
  // #endif

  uni.showLoading({ title: "正在准备文件" });
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: material.file_url,
      header: { "X-Device-ID": getDeviceId() },
      success: (result) => {
        if (result.statusCode !== 200) {
          reject(new Error(`原件下载失败（${result.statusCode}）。`));
          return;
        }
        uni.openDocument({
          filePath: result.tempFilePath,
          showMenu: true,
          success: () => resolve(true),
          fail: () => reject(new Error("当前格式无法直接预览，请用系统应用打开。")),
        });
      },
      fail: () => reject(new Error("原件下载失败，请检查网络后重试。")),
      complete: () => uni.hideLoading(),
    });
  });
}

export function absoluteMaterialUrl(value) {
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith("/")) {
    const root = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
    return `${root}${value}`;
  }
  return value;
}
