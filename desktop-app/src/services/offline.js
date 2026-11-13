import { api, isNetworkError } from "./api";

const QUEUE_KEY = "asset-library-desktop-offline-queue";
const CACHE_PREFIX = "asset-library-desktop-cache-";
const ENDPOINTS = { sale: "sales", lease: "leases", work: "work-logs", inspiration: "inspirations" };

export function cacheRecords(module, records, serverTime = new Date().toISOString()) {
  localStorage.setItem(`${CACHE_PREFIX}${module}`, JSON.stringify({ records, serverTime }));
}

export function getCachedRecords(module) {
  return JSON.parse(localStorage.getItem(`${CACHE_PREFIX}${module}`) || "null")?.records || [];
}

export function getCacheMeta(module) {
  return JSON.parse(localStorage.getItem(`${CACHE_PREFIX}${module}`) || "null");
}

export function upsertCachedRecord(module, record) {
  if (!record?.record_id) return;
  const cached = getCachedRecords(module);
  const serverTime = getCacheMeta(module)?.serverTime || new Date().toISOString();
  cacheRecords(
    module,
    [record, ...cached.filter((item) => item.record_id !== record.record_id)],
    serverTime,
  );
}

export function removeCachedRecord(module, recordId) {
  const cached = getCachedRecords(module);
  const serverTime = getCacheMeta(module)?.serverTime || new Date().toISOString();
  cacheRecords(
    module,
    cached.filter((item) => item.record_id !== recordId),
    serverTime,
  );
}

export async function cacheModuleFromServer(module) {
  const result = await api(`/sync/pull/${module}?limit=10000`);
  cacheRecords(module, result.records || [], result.server_time || new Date().toISOString());
  return result;
}

export async function cacheAllModulesFromServer() {
  const modules = Object.keys(ENDPOINTS);
  const results = await Promise.allSettled(modules.map(cacheModuleFromServer));
  return {
    cached: modules.filter((_, index) => results[index].status === "fulfilled"),
    failed: modules.filter((_, index) => results[index].status === "rejected"),
  };
}

export function enqueueOffline({ module, action, recordId, payload, clientUpdatedAt = new Date().toISOString() }) {
  const queue = JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
  const index = queue.findIndex((item) => item.module === module && item.recordId === recordId && item.action === action);
  const item = { id: crypto.randomUUID?.() || String(Date.now()), module, action, recordId, payload, clientUpdatedAt };
  if (index >= 0) queue[index] = item;
  else queue.push(item);
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  return item;
}

export function getOfflineQueue() {
  return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
}

export async function saveRecordOffline(module, recordId, payload) {
  const cached = getCachedRecords(module);
  const existing = cached.find((item) => item.record_id === recordId);
  const optimistic = { ...(existing || {}), ...payload, record_id: recordId, update_time: new Date().toISOString(), offline: true };
  upsertCachedRecord(module, optimistic);
  enqueueOffline({ module, action: "update", recordId, payload });
  return optimistic;
}

export async function flushOfflineQueue() {
  const queue = getOfflineQueue();
  const success = [];
  for (const item of queue) {
    try {
      if (item.action === "delete") {
        await api(`/${ENDPOINTS[item.module]}/${item.recordId}`, { method: "DELETE" });
      } else {
        await api("/sync/push", {
          method: "POST",
          data: {
            module: item.module,
            records: [{ record_id: item.recordId, client_updated_at: item.clientUpdatedAt, data: item.payload }],
          },
        });
      }
      success.push(item);
    } catch (error) {
      if (isNetworkError(error)) break;
      console.warn("桌面离线队列记录推送失败", error);
    }
  }
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue.filter((item) => !success.includes(item))));
  return { flushed: success.length, pending: getOfflineQueue().length };
}
