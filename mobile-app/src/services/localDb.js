import { API_BASE_URL, request, upload } from "./api";
import { getDeviceId } from "./device";

const QUEUE_KEY = "asset-library-offline-queue";
const DRAFT_KEY = "asset-library-drafts";
const CACHE_PREFIX = "asset-library-cache-";
const NATIVE_DB_NAME = "asset_library";
const NATIVE_DB_PATH = "_doc/asset_library.db";
const NATIVE_ATTACHMENT_DIR = "asset-library-attachments";
const H5_ATTACHMENT_DB = "asset-library-files";
const H5_ATTACHMENT_STORE = "attachments";

let nativeReady = null;
let flushing = false;
let h5DbReady = null;

function isNativeSqlite() {
  return typeof plus !== "undefined" && plus.sqlite && plus.os?.name;
}

function randomId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID().replace(/-/g, "");
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

function nativeExec(sql) {
  return new Promise((resolve, reject) => {
    plus.sqlite.executeSql({
      name: NATIVE_DB_NAME,
      sql,
      success: resolve,
      fail: (error) => reject(new Error(error.message || "SQLite 执行失败")),
    });
  });
}

function nativeSelect(sql) {
  return new Promise((resolve, reject) => {
    plus.sqlite.selectSql({
      name: NATIVE_DB_NAME,
      sql,
      success: resolve,
      fail: (error) => reject(new Error(error.message || "SQLite 查询失败")),
    });
  });
}

function sqlValue(value) {
  if (value === null || value === undefined) return "NULL";
  return `'${String(value).replace(/'/g, "''")}'`;
}

async function initNativeDb() {
  if (!isNativeSqlite()) return false;
  if (nativeReady) return nativeReady;
  nativeReady = new Promise((resolve, reject) => {
    plus.sqlite.openDatabase({
      name: NATIVE_DB_NAME,
      path: NATIVE_DB_PATH,
      success: async () => {
        try {
          await nativeExec(`
            CREATE TABLE IF NOT EXISTS offline_queue (
              queue_id TEXT PRIMARY KEY,
              module TEXT NOT NULL,
              action TEXT NOT NULL,
              record_id TEXT NOT NULL,
              payload TEXT,
              local_attachments TEXT,
              client_updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS draft (
              draft_id TEXT PRIMARY KEY,
              module TEXT NOT NULL,
              payload TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS record_cache (
              module TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              server_time TEXT NOT NULL
            );
          `);
          // 兼容早期安装包已创建、但没有附件列的本地方表。
          try {
            await nativeExec("ALTER TABLE offline_queue ADD COLUMN local_attachments TEXT");
          } catch (error) {
            // 列已存在时 SQLite 会报错，可安全忽略。
          }
          resolve(true);
        } catch (error) {
          reject(error);
        }
      },
      fail: (error) => reject(new Error(error.message || "本地数据库打开失败")),
    });
  });
  return nativeReady;
}

function openH5AttachmentDb() {
  if (h5DbReady) return h5DbReady;
  h5DbReady = new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("当前浏览器不支持持久文件缓存"));
      return;
    }
    const open = indexedDB.open(H5_ATTACHMENT_DB, 1);
    open.onupgradeneeded = () => {
      if (!open.result.objectStoreNames.contains(H5_ATTACHMENT_STORE)) {
        open.result.createObjectStore(H5_ATTACHMENT_STORE);
      }
    };
    open.onsuccess = () => resolve(open.result);
    open.onerror = () => reject(open.error || new Error("浏览器文件缓存打开失败"));
  });
  return h5DbReady;
}

async function putH5Attachment(id, blob) {
  const db = await openH5AttachmentDb();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(H5_ATTACHMENT_STORE, "readwrite");
    transaction.objectStore(H5_ATTACHMENT_STORE).put(blob, id);
    transaction.oncomplete = resolve;
    transaction.onerror = () => reject(transaction.error || new Error("文件写入失败"));
  });
}

async function getH5Attachment(id) {
  const db = await openH5AttachmentDb();
  return new Promise((resolve, reject) => {
    const request = db.transaction(H5_ATTACHMENT_STORE, "readonly").objectStore(H5_ATTACHMENT_STORE).get(id);
    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error || new Error("文件读取失败"));
  });
}

async function removeH5Attachment(id) {
  const db = await openH5AttachmentDb();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(H5_ATTACHMENT_STORE, "readwrite");
    transaction.objectStore(H5_ATTACHMENT_STORE).delete(id);
    transaction.oncomplete = resolve;
    transaction.onerror = () => reject(transaction.error || new Error("文件清理失败"));
  });
}

function copyNativeAttachment(file) {
  return new Promise((resolve, reject) => {
    const suffix = String(file.name || "").includes(".") ? String(file.name).split(".").pop() : "file";
    const fileName = `${randomId()}.${suffix}`;
    plus.io.requestFileSystem(plus.io.PRIVATE_DOC, (fileSystem) => {
      fileSystem.root.getDirectory(NATIVE_ATTACHMENT_DIR, { create: true }, (directory) => {
        plus.io.resolveLocalFileSystemURL(file.path, (source) => {
          source.copyTo(directory, fileName, (entry) => resolve(entry.fullPath), reject);
        }, reject);
      }, reject);
    }, reject);
  });
}

async function fileToBlob(file) {
  if (file.file instanceof Blob) return file.file;
  if (file.raw instanceof Blob) return file.raw;
  const response = await fetch(file.path);
  if (!response.ok) throw new Error("读取待传文件失败");
  return response.blob();
}

export async function persistPendingAttachments(files = []) {
  const persisted = [];
  for (const file of files) {
    if (file.local) {
      persisted.push(file.local);
      continue;
    }
    const id = randomId();
    if (isNativeSqlite()) {
      const path = await copyNativeAttachment(file);
      persisted.push({ storage: "native", id, path, name: file.name || "业务附件" });
    } else {
      const blob = await fileToBlob(file);
      await putH5Attachment(id, blob);
      persisted.push({ storage: "h5", id, name: file.name || "业务附件", type: blob.type || file.type || "" });
    }
  }
  return persisted;
}

async function uploadPersistedAttachment(item, bizType, bizId) {
  if (item.storage === "native") {
    return upload("/attachments", item.path, { biz_type: bizType, biz_id: bizId });
  }
  const blob = await getH5Attachment(item.id);
  if (!blob) throw new Error(`本地附件已缺失：${item.name}`);
  const form = new FormData();
  form.append("file", blob, item.name || "附件");
  form.append("biz_type", bizType);
  form.append("biz_id", bizId);
  const response = await fetch(`${API_BASE_URL}/attachments`, {
    method: "POST",
    headers: { "X-Device-ID": getDeviceId() },
    body: form,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `附件上传失败（${response.status}）`);
  return data;
}

async function removePersistedAttachment(item) {
  if (item.storage === "h5") {
    await removeH5Attachment(item.id);
  }
  // 原生文件由 iOS/Android 文档目录保存；上传成功后清理，避免长期占用空间。
  if (item.storage === "native" && item.path) {
    plus.io.resolveLocalFileSystemURL(item.path, (entry) => entry.remove(() => {}, () => {}), () => {});
  }
}

export async function enqueueOffline({ module, action, recordId, payload, clientUpdatedAt, localAttachments = [] }) {
  const item = {
    queue_id: randomId(),
    module,
    action,
    record_id: recordId,
    payload,
    local_attachments: localAttachments,
    client_updated_at: clientUpdatedAt || new Date().toISOString(),
  };
  if (await initNativeDb()) {
    await nativeExec(`
      INSERT INTO offline_queue (queue_id, module, action, record_id, payload, local_attachments, client_updated_at)
      VALUES (${sqlValue(item.queue_id)}, ${sqlValue(module)}, ${sqlValue(action)}, ${sqlValue(recordId)},
        ${sqlValue(JSON.stringify(payload || {}))}, ${sqlValue(JSON.stringify(localAttachments))}, ${sqlValue(item.client_updated_at)})
    `);
  } else {
    const queue = uni.getStorageSync(QUEUE_KEY) || [];
    queue.push(item);
    uni.setStorageSync(QUEUE_KEY, queue);
  }
  uni.$emit("offline-queue-changed", { pending: (await listOfflineQueue()).length });
  return item;
}

export async function listOfflineQueue() {
  if (await initNativeDb()) {
    const rows = await nativeSelect("SELECT * FROM offline_queue ORDER BY client_updated_at ASC");
    return rows.map((row) => ({
      ...row,
      payload: JSON.parse(row.payload || "{}"),
      local_attachments: JSON.parse(row.local_attachments || "[]"),
    }));
  }
  return uni.getStorageSync(QUEUE_KEY) || [];
}

async function removeQueueItem(queueId) {
  if (await initNativeDb()) {
    await nativeExec(`DELETE FROM offline_queue WHERE queue_id = ${sqlValue(queueId)}`);
  } else {
    const queue = (uni.getStorageSync(QUEUE_KEY) || []).filter((item) => item.queue_id !== queueId);
    uni.setStorageSync(QUEUE_KEY, queue);
  }
}

const endpoints = { sale: "sales", lease: "leases", work: "work-logs", inspiration: "inspirations" };

export async function flushOfflineQueue() {
  if (flushing) return { skipped: true };
  const network = await new Promise((resolve) => {
    uni.getNetworkType({
      success: (result) => resolve(result.networkType !== "none"),
      fail: () => resolve(false),
    });
  });
  if (!network) return { skipped: true, offline: true };
  flushing = true;
  const queue = await listOfflineQueue();
  const result = { accepted: 0, conflicts: 0, failed: 0 };
  for (const item of queue) {
    try {
      if (item.action === "delete") {
        await request(`/${endpoints[item.module]}/${item.record_id}`, { method: "DELETE" });
      } else {
        const response = await request("/sync/push", {
          method: "POST",
          data: {
            module: item.module,
            records: [
              {
                record_id: item.record_id,
                client_updated_at: item.client_updated_at,
                data: item.payload,
              },
            ],
          },
        });
        if (response.conflicts?.length) {
          result.conflicts += 1;
          continue;
        }
        for (const attachment of item.local_attachments || []) {
          await uploadPersistedAttachment(attachment, item.module, item.record_id);
          await removePersistedAttachment(attachment);
        }
      }
      await removeQueueItem(item.queue_id);
      result.accepted += 1;
    } catch (error) {
      result.failed += 1;
      console.warn("离线队列同步失败", error);
      // 权限冲突保留在队列中，避免用户刚录的内容被静默丢弃。
      if (error.status && error.status >= 500) break;
    }
  }
  flushing = false;
  uni.$emit("offline-queue-flushed", result);
  return result;
}

export async function saveDraft(module, payload) {
  const draft = {
    draft_id: randomId(),
    module,
    payload,
    updated_at: new Date().toISOString(),
  };
  if (await initNativeDb()) {
    await nativeExec(`
      INSERT INTO draft (draft_id, module, payload, updated_at)
      VALUES (${sqlValue(draft.draft_id)}, ${sqlValue(module)}, ${sqlValue(JSON.stringify(payload))}, ${sqlValue(draft.updated_at)})
    `);
  } else {
    const drafts = uni.getStorageSync(DRAFT_KEY) || [];
    drafts.unshift(draft);
    uni.setStorageSync(DRAFT_KEY, drafts.slice(0, 100));
  }
  return draft;
}

export async function listDrafts() {
  if (await initNativeDb()) {
    const rows = await nativeSelect("SELECT * FROM draft ORDER BY updated_at DESC LIMIT 100");
    return rows.map((row) => ({ ...row, payload: JSON.parse(row.payload) }));
  }
  return uni.getStorageSync(DRAFT_KEY) || [];
}

export async function removeDraft(draftId) {
  if (await initNativeDb()) {
    await nativeExec(`DELETE FROM draft WHERE draft_id = ${sqlValue(draftId)}`);
  } else {
    const drafts = (uni.getStorageSync(DRAFT_KEY) || []).filter((item) => item.draft_id !== draftId);
    uni.setStorageSync(DRAFT_KEY, drafts);
  }
}

export async function cacheRecords(module, records, serverTime) {
  if (await initNativeDb()) {
    await nativeExec(`
      INSERT OR REPLACE INTO record_cache (module, payload, server_time)
      VALUES (${sqlValue(module)}, ${sqlValue(JSON.stringify(records))}, ${sqlValue(serverTime || new Date().toISOString())})
    `);
  } else {
    uni.setStorageSync(`${CACHE_PREFIX}${module}`, {
      records,
      serverTime: serverTime || new Date().toISOString(),
    });
  }
}

export async function getCachedRecords(module) {
  if (await initNativeDb()) {
    const rows = await nativeSelect(`SELECT payload FROM record_cache WHERE module = ${sqlValue(module)} LIMIT 1`);
    return rows[0] ? JSON.parse(rows[0].payload) : [];
  }
  return uni.getStorageSync(`${CACHE_PREFIX}${module}`)?.records || [];
}
