const PENDING_PLAN_KEY = "asset-library-pending-plan-review";

export function storePlanReview({ candidates, provider = "", rawText = "", source = "entry" }) {
  const payload = {
    candidates: Array.isArray(candidates) ? candidates.slice(0, 20) : [],
    provider,
    rawText: String(rawText || ""),
    source,
    created_at: Date.now(),
  };
  uni.setStorageSync(PENDING_PLAN_KEY, payload);
  return payload;
}

export function consumePlanReview() {
  const payload = uni.getStorageSync(PENDING_PLAN_KEY);
  uni.removeStorageSync(PENDING_PLAN_KEY);
  if (!payload || !Array.isArray(payload.candidates) || !payload.candidates.length) return null;
  return payload;
}

export function clearPlanReview() {
  uni.removeStorageSync(PENDING_PLAN_KEY);
}

export { PENDING_PLAN_KEY };
