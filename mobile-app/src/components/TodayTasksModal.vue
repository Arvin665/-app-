<template>
  <view v-if="rendered" class="today-tasks-layer" :class="{ 'is-active': active }" @tap="requestClose">
    <view class="today-card" @tap.stop>
      <view class="card-accent"></view>

      <view class="modal-head">
        <view class="head-icon"><CalendarCheck2 :size="19" /></view>
        <view class="head-copy">
          <text class="head-kicker">TODAY'S FOCUS</text>
          <text class="head-title">今天先做这些</text>
          <text class="head-date">{{ readableDate }}</text>
        </view>
        <view class="close-button pressable" @tap="requestClose">
          <X :size="17" />
        </view>
      </view>

      <view v-if="plans.length || (!loading && !error)" class="progress-section">
        <view class="progress-meta">
          <view>
            <text class="progress-number">{{ completedCount }}</text>
            <text class="progress-total"> / {{ plans.length }}</text>
            <text class="progress-label">项已完成</text>
          </view>
          <text class="progress-percent">{{ completionPercent }}%</text>
        </view>
        <view class="progress-track">
          <view class="progress-fill" :style="{ width: `${completionPercent}%` }"></view>
        </view>
      </view>

      <scroll-view class="task-scroll" scroll-y :style="{ height: listHeight }">
        <view v-if="loading && !plans.length" class="loading-tasks">
          <view class="loading-icon"><LoaderCircle :size="20" class="spin" /></view>
          <text class="empty-title">正在整理今日事项</text>
          <text class="empty-note">请稍等，正在同步计划和完成进度。</text>
        </view>
        <view v-else-if="!plans.length" class="empty-tasks" :class="{ 'is-error': error }">
          <view v-if="error" class="empty-icon"><CloudOff :size="19" /></view>
          <text class="empty-title">{{ error ? "今日待办暂时没同步" : "今天还没有待办" }}</text>
          <text class="empty-note">{{ error || "可以先进入计划页，用语音或文字添加。" }}</text>
          <view v-if="error" class="empty-retry pressable" @tap.stop="retry">重新同步</view>
        </view>
        <view v-for="plan in plans" :key="plan.record_id" class="task-row">
          <view class="task-head">
            <text class="task-time">{{ plan.ext_field_4 || "全天" }}</text>
            <view class="task-copy">
              <text class="task-title">{{ plan.content || "未填写计划内容" }}</text>
              <text v-if="plan.related_project" class="task-project">{{ plan.related_project }}</text>
            </view>
            <text class="task-state" :class="`tone-${statusTone(plan)}`">
              {{ updatingId === plan.record_id ? "保存中" : statusLabel(plan) }}
            </text>
          </view>

          <text v-if="latestNote(plan.ext_field_1)" class="task-note">{{ latestNote(plan.ext_field_1) }}</text>

          <view v-if="!locked" class="task-actions">
            <view
              v-for="item in statuses"
              :key="item.value"
              class="status-button pressable"
              :class="[
                `tone-${item.tone}`,
                { selected: planStatus(plan) === item.value, disabled: updatingId === plan.record_id },
              ]"
              @tap="selectStatus(plan, item.value)"
            >
              <view class="status-dot"></view>
              <text>{{ item.short }}</text>
            </view>
          </view>
        </view>
      </scroll-view>

      <view v-if="locked" class="locked-note">
        <Check :size="14" />
        <text>今天的计划已经归档，当前仅可查看。</text>
      </view>

      <view class="modal-footer">
        <view class="plan-link pressable" @tap="openPlans">查看全部计划</view>
        <view class="home-action pressable" @tap="requestClose">
          <text>进入首页</text>
          <ChevronRight :size="15" />
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { CalendarCheck2, Check, ChevronRight, CloudOff, LoaderCircle, X } from "@lucide/vue";

const props = defineProps({
  visible: Boolean,
  plans: { type: Array, default: () => [] },
  date: { type: String, default: "" },
  locked: Boolean,
  updatingId: { type: String, default: "" },
  loading: Boolean,
  error: { type: String, default: "" },
});

const emit = defineEmits(["close", "update-status", "open-plans", "retry"]);

const statuses = [
  { value: 0, short: "未做", tone: "idle" },
  { value: 1, short: "进行中", tone: "running" },
  { value: 2, short: "完成", tone: "done" },
  { value: 3, short: "搁置", tone: "paused" },
];
const statusMeta = {
  0: { label: "未做", tone: "idle" },
  1: { label: "进行中", tone: "running" },
  2: { label: "已做好", tone: "done" },
  3: { label: "已搁置", tone: "paused" },
};

const rendered = ref(false);
const active = ref(false);
let enterTimer = null;
let exitTimer = null;

const completedCount = computed(
  () => props.plans.filter((plan) => Number(plan.ext_field_5 ?? 0) === 2).length,
);
const completionPercent = computed(() => (
  props.plans.length ? Math.round((completedCount.value / props.plans.length) * 100) : 0
));
const listHeight = computed(() => {
  if (props.error && !props.plans.length) return "156px";
  return `${Math.min(330, Math.max(112, props.plans.length * 90))}px`;
});
const readableDate = computed(() => formatDate(props.date));

watch(
  () => props.visible,
  (visible) => {
    clearTimeout(enterTimer);
    clearTimeout(exitTimer);
    if (visible) {
      rendered.value = true;
      enterTimer = setTimeout(() => {
        active.value = true;
      }, 20);
      return;
    }
    active.value = false;
    if (rendered.value) {
      exitTimer = setTimeout(() => {
        rendered.value = false;
      }, 220);
    }
  },
  { immediate: true },
);

function planStatus(plan) {
  const value = Number(plan.ext_field_5 ?? 0);
  return value >= 0 && value <= 3 ? value : 0;
}

function statusLabel(plan) {
  return statusMeta[planStatus(plan)].label;
}

function statusTone(plan) {
  return statusMeta[planStatus(plan)].tone;
}

function selectStatus(plan, status) {
  if (props.locked || props.updatingId === plan.record_id || planStatus(plan) === status) return;
  emit("update-status", { plan, status });
}

function latestNote(value) {
  const lines = String(value || "").split("\n").filter(Boolean);
  return lines[lines.length - 1] || "";
}

function formatDate(value) {
  const [year, month, day] = String(value || "").split("-").map(Number);
  if (!year || !month || !day) return value || "";
  const weekday = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][new Date(year, month - 1, day).getDay()];
  return `${month} 月 ${day} 日 · ${weekday}`;
}

function requestClose() {
  emit("close");
}

function openPlans() {
  emit("open-plans");
}

function retry() {
  emit("retry");
}

onUnmounted(() => {
  clearTimeout(enterTimer);
  clearTimeout(exitTimer);
});
</script>

<style scoped>
.today-tasks-layer {
  position: fixed;
  z-index: 1200;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: calc(20px + env(safe-area-inset-top)) 16px calc(20px + env(safe-area-inset-bottom));
  background: rgba(13, 25, 21, 0.48);
  opacity: 0;
  transition: opacity 180ms ease;
}
.today-tasks-layer.is-active {
  opacity: 1;
}
.today-card {
  width: 100%;
  max-width: 340px;
  max-height: 74vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(220, 229, 225, 0.95);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: 0 24px 64px rgba(10, 31, 25, 0.26);
  opacity: 0;
  transform: translateY(16px) scale(0.968);
  transition:
    opacity 180ms ease,
    transform 240ms cubic-bezier(0.2, 0.75, 0.25, 1);
}
.today-tasks-layer.is-active .today-card {
  opacity: 1;
  transform: translateY(0) scale(1);
}
.card-accent {
  height: 3px;
  flex: none;
  background: var(--accent);
}
.modal-head {
  flex: none;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 15px 15px 10px;
}
.head-icon {
  width: 36px;
  height: 36px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #cce7df;
  border-radius: 8px;
  background: var(--accent-soft);
  color: var(--accent);
}
.head-copy {
  flex: 1;
  min-width: 0;
}
.head-kicker {
  display: block;
  color: var(--accent);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0;
  line-height: 12px;
}
.head-title {
  display: block;
  margin-top: 1px;
  color: var(--ink);
  font-size: 20px;
  font-weight: 760;
  line-height: 27px;
}
.head-date {
  display: block;
  margin-top: 1px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 15px;
}
.close-button {
  width: 34px;
  height: 34px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: #f7f9f8;
  color: var(--text-secondary);
}
.progress-section {
  flex: none;
  margin: 0 15px 10px;
  padding: 10px 11px;
  border: 1px solid #d2e8e2;
  border-radius: 8px;
  background: #f4faf8;
}
.progress-meta {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}
.progress-number {
  color: var(--ink);
  font-size: 18px;
  font-weight: 760;
  line-height: 21px;
}
.progress-total {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 550;
}
.progress-label {
  display: inline-block;
  margin-left: 4px;
  color: var(--text-secondary);
  font-size: 9px;
}
.progress-percent {
  color: var(--accent);
  font-size: 9px;
  font-weight: 720;
}
.progress-track {
  height: 5px;
  margin-top: 7px;
  overflow: hidden;
  border-radius: 3px;
  background: #dcebe7;
}
.progress-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--accent);
  transition: width 220ms ease;
}
.task-scroll {
  min-height: 112px;
  flex: none;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  background: #ffffff;
}
.task-row {
  padding: 11px 15px 10px;
  border-bottom: 1px solid var(--border);
}
.task-row:last-child {
  border-bottom: 0;
}
.task-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.task-time {
  width: 38px;
  flex: none;
  padding-top: 2px;
  color: var(--accent);
  font-size: 9px;
  font-weight: 700;
  line-height: 15px;
}
.task-copy {
  flex: 1;
  min-width: 0;
}
.task-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
  line-height: 18px;
  overflow-wrap: anywhere;
}
.task-project {
  display: block;
  margin-top: 2px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-state {
  min-width: 42px;
  flex: none;
  padding: 3px 6px;
  border-radius: 5px;
  font-size: 8px;
  font-weight: 650;
  line-height: 12px;
  text-align: center;
}
.task-state.tone-idle {
  background: var(--soft);
  color: var(--text-secondary);
}
.task-state.tone-running {
  background: var(--info-bg);
  color: var(--info);
}
.task-state.tone-done {
  background: var(--success-bg);
  color: var(--success);
}
.task-state.tone-paused {
  background: var(--warning-bg);
  color: var(--warning);
}
.task-note {
  display: block;
  margin: 6px 0 0 46px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 8px;
  line-height: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 4px;
  margin: 8px 0 0 46px;
}
.status-button {
  min-width: 0;
  height: 29px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 0 3px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #ffffff;
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 620;
}
.status-button.disabled {
  opacity: 0.58;
}
.status-dot {
  width: 4px;
  height: 4px;
  flex: none;
  border-radius: 50%;
  background: currentColor;
}
.status-button.tone-running.selected {
  border-color: #bfd3df;
  background: var(--info-bg);
  color: var(--info);
}
.status-button.tone-done.selected {
  border-color: #b9ddd3;
  background: var(--success-bg);
  color: var(--success);
}
.status-button.tone-paused.selected {
  border-color: #e7ccb7;
  background: var(--warning-bg);
  color: var(--warning);
}
.status-button.tone-idle.selected {
  border-color: #cdd8d3;
  background: var(--soft);
  color: var(--text-secondary);
}
.empty-tasks {
  height: 112px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px;
}
.loading-tasks {
  height: 112px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px;
}
.loading-icon {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 7px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.empty-tasks.is-error {
  height: 156px;
}
.empty-icon {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 7px;
  border-radius: 50%;
  background: var(--danger-bg);
  color: var(--danger);
}
.empty-title {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}
.empty-note {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 14px;
  text-align: center;
}
.empty-retry {
  min-height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 9px;
  padding: 0 12px;
  border: 1px solid #e5c8c3;
  border-radius: 6px;
  background: var(--danger-bg);
  color: var(--danger);
  font-size: 9px;
  font-weight: 650;
}
.locked-note {
  flex: none;
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 9px 15px 0;
  padding: 8px 9px;
  border-radius: 6px;
  background: var(--success-bg);
  color: var(--accent-deep);
  font-size: 9px;
  line-height: 14px;
}
.modal-footer {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 15px 13px;
  background: #fbfcfb;
}
.plan-link {
  min-height: 40px;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 600;
}
.home-action {
  height: 40px;
  flex: 1.2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border-radius: 7px;
  background: var(--accent);
  color: #ffffff;
  font-size: 11px;
  font-weight: 680;
}
@media (max-height: 620px) {
  .modal-head {
    padding-top: 12px;
  }
  .head-title {
    font-size: 18px;
    line-height: 24px;
  }
  .progress-section {
    padding-top: 8px;
    padding-bottom: 8px;
  }
  .task-scroll {
    max-height: 38vh;
  }
}
@media (prefers-reduced-motion: reduce) {
  .today-tasks-layer,
  .today-card,
  .progress-fill {
    transition: none;
  }
}
</style>
