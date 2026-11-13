<template>
  <view class="plans-page">
    <PageHeader title="工作记录" fallback="/pages/home/index">
      <template #actions>
        <text class="header-action" @tap="goProfile">我的</text>
      </template>
    </PageHeader>

    <view class="tabs">
      <view class="tab" :class="{ active: tab === 'all' }" @tap="tab = 'all'; loadAll()">全部记录</view>
      <view class="tab" :class="{ active: tab === 'plans' }" @tap="tab = 'plans'; loadPlans()">待办计划</view>
    </view>

    <view v-if="tab === 'plans' && todayPlans.length" class="daily-banner" @tap="openDaily">
      <text>今日 {{ todayPlans.length }} 项计划{{ dailyLocked ? "已归档" : "待确认" }}</text>
      <text class="banner-action">{{ dailyLocked ? "查看" : "去确认" }}</text>
    </view>

    <scroll-view class="list-scroll" scroll-y>
      <template v-if="tab === 'all'">
        <view v-if="!records.length && !loading" class="empty-state">当前没有工作记录</view>
        <view v-for="record in records" :key="record.record_id" class="record-card" @tap="openDetail(record)">
          <view class="record-head">
            <text class="record-type">{{ record.record_type }}</text>
            <text class="record-date">{{ record.record_date }}</text>
          </view>
          <text class="record-content">{{ record.content }}</text>
          <view class="record-meta">
            <text>{{ record.related_project || (record.is_shared ? "团队共享" : "仅本人可见") }}</text>
            <text v-if="record.record_type === '待办计划'">{{ statusMap[Number(record.ext_field_5)] || "未做" }}</text>
          </view>
        </view>
      </template>

      <template v-else>
        <view v-if="!activePlans.length && !completedPlans.length && !loading" class="empty-state">没有待办计划</view>
        <template v-if="activePlans.length">
          <text class="group-title">待处理</text>
          <view v-for="plan in activePlans" :key="plan.record_id" class="plan-card" @tap="openDetail(plan)">
            <view class="plan-row">
              <view class="plan-summary">
                <text class="plan-time">{{ plan.ext_field_4 || "全天" }}</text>
                <text class="plan-content">{{ plan.content }}</text>
                <text class="plan-project">{{ plan.related_project || "" }}</text>
              </view>
              <view class="plan-actions">
                <view class="status-grid">
                  <button
                    v-for="item in statuses"
                    :key="item.value"
                    class="status-button"
                    :class="{ selected: Number(plan.ext_field_5) === item.value }"
                    @tap.stop="changeStatus(plan, item)"
                  >
                    {{ item.short }}
                  </button>
                </view>
                <text class="postpone-link" @tap.stop="openPostpone(plan)">推迟</text>
              </view>
            </view>
            <text v-if="plan.ext_field_1" class="execution-note">{{ plan.ext_field_1 }}</text>
          </view>
        </template>

        <template v-if="completedPlans.length">
          <text class="group-title completed-title">已完成</text>
          <view v-for="plan in completedPlans" :key="plan.record_id" class="plan-card completed" @tap="openDetail(plan)">
            <view class="plan-row">
              <view class="plan-summary">
                <text class="plan-time">{{ plan.ext_field_4 || "全天" }}</text>
                <text class="plan-content">{{ plan.content }}</text>
              </view>
              <view class="plan-actions">
                <view class="status-grid">
                  <button
                    v-for="item in statuses"
                    :key="item.value"
                    class="status-button"
                    :class="{ selected: Number(plan.ext_field_5) === item.value }"
                    @tap.stop="changeStatus(plan, item)"
                  >
                    {{ item.short }}
                  </button>
                </view>
                <text class="postpone-link" @tap.stop="openPostpone(plan)">推迟</text>
              </view>
            </view>
            <text v-if="plan.ext_field_1" class="execution-note">{{ plan.ext_field_1 }}</text>
          </view>
        </template>
      </template>
    </scroll-view>

    <view v-if="noteModal.visible" class="modal-mask" @tap="closeNote">
      <view class="note-dialog" @tap.stop>
        <text class="note-title">{{ noteModal.label }}计划</text>
        <text class="note-desc">{{ noteModal.placeholder }}</text>
        <textarea v-model="noteModal.note" class="note-textarea" maxlength="500" :placeholder="noteModal.placeholder" />
        <view class="dialog-actions">
          <button class="cancel-button" @tap="closeNote">取消</button>
          <button class="confirm-button" @tap="submitStatus">保存状态</button>
        </view>
      </view>
    </view>

    <view v-if="postpone.visible" class="modal-mask" @tap="closePostpone">
      <view class="postpone-dialog" @tap.stop>
        <text class="note-title">推迟计划</text>
        <text class="postpone-original">原计划：{{ postpone.plan?.record_date }} {{ postpone.plan?.ext_field_4 || "全天" }}</text>
        <view class="postpone-field">
          <text>新日期</text>
          <picker mode="date" :value="postpone.date" @change="postpone.date = $event.detail.value">
            <view class="picker-box">{{ postpone.date }}</view>
          </picker>
        </view>
        <view class="postpone-field">
          <text>新时间</text>
          <picker mode="time" :value="postpone.time" @change="postpone.time = $event.detail.value">
            <view class="picker-box">{{ postpone.time || "全天" }}</view>
          </picker>
        </view>
        <textarea v-model="postpone.reason" class="note-textarea" maxlength="500" placeholder="填写推迟原因" />
        <view class="dialog-actions">
          <button class="cancel-button" @tap="closePostpone">取消</button>
          <button class="confirm-button" @tap="submitPostpone">确认推迟</button>
        </view>
      </view>
    </view>

    <DailyConfirmModal
      :visible="dailyModal"
      :plans="todayPlans"
      :record-date="today"
      :saving="archiving"
      @close="dailyModal = false; rememberDismiss()"
      @archive="archiveDaily"
      @update-plan="updateFromDaily"
    />
  </view>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { onLoad, onPullDownRefresh, onShow, onUnload } from "@dcloudio/uni-app";
import PageHeader from "../../components/PageHeader.vue";
import DailyConfirmModal from "../../components/DailyConfirmModal.vue";
import { request } from "../../services/api";
import { cacheRecords, enqueueOffline, getCachedRecords } from "../../services/localDb";
import { localDate, normalizeRecordPayload } from "../../data/modules";
import { cancelPlanReminder, schedulePlanReminder } from "../../services/reminders";

const tab = ref("plans");
const records = ref([]);
const plans = ref([]);
const todayPlans = ref([]);
const loading = ref(false);
const dailyLocked = ref(false);
const dailyModal = ref(false);
const archiving = ref(false);
const today = localDate();
const todayKey = `daily-dismissed-${today}`;
let clock = null;

const statuses = [
  { value: 0, label: "未做", short: "未做" },
  { value: 1, label: "正在做", short: "正在做" },
  { value: 2, label: "已做好", short: "已做好" },
  { value: 3, label: "计划搁置", short: "搁置" },
];
const statusMap = { 0: "未做", 1: "正在做", 2: "已做好", 3: "计划搁置" };

const activePlans = computed(() =>
  plans.value.filter((item) => Number(item.ext_field_5) !== 2).sort((a, b) => `${a.record_date}${a.ext_field_4 || ""}`.localeCompare(`${b.record_date}${b.ext_field_4 || ""}`)),
);
const completedPlans = computed(() =>
  plans.value.filter((item) => Number(item.ext_field_5) === 2).sort((a, b) => `${b.record_date}${b.ext_field_4 || ""}`.localeCompare(`${a.record_date}${a.ext_field_4 || ""}`)),
);

const noteModal = reactive({ visible: false, plan: null, status: 0, label: "", placeholder: "", note: "" });
const postpone = reactive({ visible: false, plan: null, date: today, time: "09:00", reason: "" });

async function loadAll() {
  loading.value = true;
  try {
    const result = await request("/work-logs?page_size=500");
    records.value = result.items;
    await cacheRecords("work", result.items, new Date().toISOString());
  } catch (error) {
    records.value = await getCachedRecords("work");
    if (!records.value.length) uni.showToast({ title: "网络不可用，暂无本地缓存", icon: "none" });
  } finally {
    loading.value = false;
  }
}

async function loadPlans() {
  loading.value = true;
  try {
    const [planResult, todayResult] = await Promise.all([
      request("/work-logs?record_type=待办计划&page_size=500"),
      request(`/work-logs/plans?record_date=${today}`),
    ]);
    plans.value = planResult.items;
    todayPlans.value = todayResult.items;
    dailyLocked.value = todayResult.locked;
    plans.value.forEach((plan) => schedulePlanReminder(plan));
  } catch (error) {
    const cached = await getCachedRecords("work");
    plans.value = cached.filter((item) => item.record_type === "待办计划");
    todayPlans.value = plans.value.filter((item) => item.record_date === today);
    uni.showToast({ title: "网络不可用，已显示本地计划", icon: "none" });
  } finally {
    loading.value = false;
  }
}

function maybeOpenDaily() {
  const now = new Date();
  const after = now.getHours() > 17 || (now.getHours() === 17 && now.getMinutes() >= 30);
  const dismissed = uni.getStorageSync(todayKey);
  if (after && todayPlans.value.length && !dailyLocked.value && !dismissed) dailyModal.value = true;
}

function openDaily() {
  dailyModal.value = true;
}

function rememberDismiss() {
  uni.setStorageSync(todayKey, true);
}

function goProfile() {
  uni.navigateTo({ url: "/pages/profile/index" });
}

function openDetail(record) {
  uni.navigateTo({ url: `/pages/detail/index?module=work&id=${record.record_id}` });
}

function changeStatus(plan, item) {
  if (dailyLocked.value && item.value !== Number(plan.ext_field_5)) {
    uni.showToast({ title: "今日计划已归档锁定", icon: "none" });
    return;
  }
  if (item.value === 0) {
    submitPlanStatus(plan, 0, "");
    return;
  }
  noteModal.visible = true;
  noteModal.plan = plan;
  noteModal.status = item.value;
  noteModal.label = item.label;
  noteModal.note = "";
  noteModal.placeholder = item.value === 1 ? "填写当前进展" : item.value === 2 ? "填写完成情况与心得" : "填写搁置原因";
}

function closeNote() {
  noteModal.visible = false;
  noteModal.plan = null;
}

async function submitStatus() {
  if (!noteModal.note.trim()) {
    uni.showToast({ title: noteModal.placeholder, icon: "none" });
    return;
  }
  const plan = noteModal.plan;
  const status = noteModal.status;
  const note = noteModal.note.trim();
  closeNote();
  await submitPlanStatus(plan, status, note);
}

function statusPayload(plan, status, note) {
  const line = `[${new Date().toLocaleString()}] ${statusMap[status]}：${note}`;
  return {
    ...plan,
    ext_field_5: status,
    ext_field_1: note ? `${plan.ext_field_1 || ""}\n${line}`.trim() : plan.ext_field_1,
  };
}

async function submitPlanStatus(plan, status, note) {
  try {
    let updated;
    try {
      updated = await request(`/work-logs/${plan.record_id}/status`, {
        method: "POST",
        data: { status, note },
      });
    } catch (error) {
      if (!/network|timeout|fail/i.test(error.message || "") && error.status !== 0) throw error;
      updated = statusPayload(plan, status, note);
      await enqueueOffline({
        module: "work",
        action: "update",
        recordId: plan.record_id,
        payload: normalizeRecordPayload("work", updated),
        clientUpdatedAt: new Date().toISOString(),
      });
    }
    replacePlan(updated);
    if ([2, 3].includes(status)) cancelPlanReminder(plan.record_id);
    else schedulePlanReminder(updated);
    uni.showToast({ title: "状态已更新", icon: "success" });
  } catch (error) {
    uni.showToast({ title: error.message || "状态更新失败", icon: "none" });
  }
}

function replacePlan(updated) {
  plans.value = plans.value.map((item) => (item.record_id === updated.record_id ? { ...item, ...updated } : item));
  todayPlans.value = todayPlans.value.map((item) => (item.record_id === updated.record_id ? { ...item, ...updated } : item));
}

async function updateFromDaily({ plan, status, note }) {
  await submitPlanStatus(plan, status, note);
}

function openPostpone(plan) {
  postpone.visible = true;
  postpone.plan = plan;
  postpone.date = plan.record_date || today;
  postpone.time = plan.ext_field_4 || "09:00";
  postpone.reason = "";
}

function closePostpone() {
  postpone.visible = false;
  postpone.plan = null;
}

async function submitPostpone() {
  if (!postpone.plan || !postpone.reason.trim()) {
    uni.showToast({ title: "请填写推迟原因", icon: "none" });
    return;
  }
  const plan = postpone.plan;
  const newDate = postpone.date;
  const newTime = postpone.time;
  const reason = postpone.reason.trim();
  const history = (() => {
    try {
      return plan.ext_field_2 ? JSON.parse(plan.ext_field_2) : [];
    } catch (error) {
      return [];
    }
  })();
  history.push({
    from_date: plan.record_date,
    from_time: plan.ext_field_4,
    to_date: newDate,
    to_time: newTime,
    reason,
    postponed_at: new Date().toISOString(),
  });
  const optimistic = { ...plan, record_date: newDate, ext_field_4: newTime, ext_field_2: JSON.stringify(history) };
  try {
    let updated;
    try {
      updated = await request(`/work-logs/${plan.record_id}/postpone`, {
        method: "POST",
        data: { new_date: newDate, new_time: newTime, reason },
      });
    } catch (error) {
      if (!/network|timeout|fail/i.test(error.message || "") && error.status !== 0) throw error;
      updated = optimistic;
      await enqueueOffline({
        module: "work",
        action: "update",
        recordId: plan.record_id,
        payload: normalizeRecordPayload("work", optimistic),
        clientUpdatedAt: new Date().toISOString(),
      });
    }
    cancelPlanReminder(plan.record_id);
    schedulePlanReminder(updated);
    replacePlan(updated);
    closePostpone();
    loadPlans();
    uni.showToast({ title: "计划已推迟", icon: "success" });
  } catch (error) {
    uni.showToast({ title: error.message || "推迟失败", icon: "none" });
  }
}

async function archiveDaily(insight) {
  if (!todayPlans.value.length) {
    uni.showToast({ title: "今天没有计划可归档", icon: "none" });
    return;
  }
  archiving.value = true;
  try {
    await request("/work-logs/archive-daily", {
      method: "POST",
      data: { record_date: today, insight },
    });
    dailyLocked.value = true;
    dailyModal.value = false;
    todayPlans.value.forEach((plan) => cancelPlanReminder(plan.record_id));
    uni.showToast({ title: "已归档为每日复盘", icon: "success" });
    await Promise.all([loadAll(), loadPlans()]);
  } catch (error) {
    uni.showToast({ title: error.message || "归档失败，请联网后重试", icon: "none" });
  } finally {
    archiving.value = false;
  }
}

onLoad(() => {
  loadAll();
  loadPlans();
  clock = setInterval(() => {
    maybeOpenDaily();
  }, 30000);
});

onShow(() => {
  loadPlans();
  maybeOpenDaily();
});

onPullDownRefresh(async () => {
  await Promise.all([loadAll(), loadPlans()]);
  uni.stopPullDownRefresh();
});

onUnload(() => {
  if (clock) clearInterval(clock);
});
</script>

<style scoped>
.plans-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--page-bg);
}
.header-action {
  color: var(--accent);
  font-size: 13px;
}
.tabs {
  flex: none;
  height: 44px;
  display: flex;
  align-items: flex-end;
  gap: 24px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}
.tab {
  height: 44px;
  padding-bottom: 10px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 24px;
}
.tab.active {
  border-bottom: 2px solid var(--accent);
  color: var(--accent);
  font-weight: 600;
}
.daily-banner {
  flex: none;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: var(--warning-bg);
  color: var(--warning);
  font-size: 12px;
}
.banner-action {
  font-weight: 600;
}
.list-scroll {
  flex: 1;
  min-height: 0;
  padding-bottom: env(safe-area-inset-bottom);
}
.record-card,
.plan-card {
  margin: 12px 16px 0;
  padding: 14px;
  border-radius: 8px;
  background: var(--surface);
}
.record-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.record-type {
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
}
.record-date {
  color: var(--text-muted);
  font-size: 11px;
}
.record-content {
  display: -webkit-box;
  margin-top: 8px;
  overflow: hidden;
  font-size: 15px;
  font-weight: 500;
  line-height: 22px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.record-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 11px;
}
.group-title {
  display: block;
  padding: 14px 16px 0;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}
.completed-title {
  margin-top: 4px;
}
.plan-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.plan-summary {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.plan-time {
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 600;
}
.plan-content {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 20px;
}
.plan-project {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 11px;
}
.plan-actions {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.status-grid {
  display: flex;
  gap: 3px;
}
.status-button {
  width: 42px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 10px;
  line-height: 26px;
}
.status-button.selected {
  border-color: var(--accent);
  background: var(--accent);
  color: #ffffff;
}
.postpone-link {
  margin-top: 6px;
  color: var(--accent);
  font-size: 11px;
}
.execution-note {
  display: block;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 11px;
  line-height: 17px;
  white-space: pre-wrap;
}
.plan-card.completed {
  opacity: 0.78;
}
.modal-mask {
  position: fixed;
  z-index: 900;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: env(safe-area-inset-top) 16px env(safe-area-inset-bottom);
  background: rgba(0, 0, 0, 0.32);
}
.note-dialog,
.postpone-dialog {
  width: 100%;
  padding: 16px;
  border-radius: 8px;
  background: var(--surface);
}
.note-title {
  display: block;
  font-size: 16px;
  font-weight: 600;
}
.note-desc,
.postpone-original {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 12px;
}
.note-textarea {
  width: 100%;
  height: 96px;
  margin-top: 12px;
  padding: 10px;
  border-radius: 4px;
  background: var(--page-bg);
  color: var(--text-primary);
  font-size: 13px;
  line-height: 19px;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
.cancel-button,
.confirm-button {
  height: 36px;
  padding: 0 16px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 36px;
}
.cancel-button {
  background: var(--page-bg);
  color: var(--text-secondary);
}
.confirm-button {
  background: var(--accent);
  color: #ffffff;
}
.postpone-field {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  border-bottom: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 13px;
}
.picker-box {
  color: var(--text-primary);
}
</style>
