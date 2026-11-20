<template>
  <view class="reminders-page app-page">
    <PageHeader title="提醒服务" fallback="/pages/profile/index">
      <template #actions>
        <view class="header-action pressable" @tap="loadPage">
          <LoaderCircle v-if="loading" :size="15" class="spin" />
          <RefreshCw v-else :size="15" />
          <text>刷新</text>
        </view>
      </template>
    </PageHeader>

    <scroll-view class="reminders-scroll" scroll-y>
      <view class="service-hero" :class="`tone-${permissionTone}`">
        <view class="hero-pattern"></view>
        <view class="hero-head">
          <view class="hero-icon">
            <LoaderCircle v-if="permission === 'checking'" :size="24" class="spin" />
            <BellRing v-else-if="permission === 'granted'" :size="24" />
            <BellOff v-else :size="24" />
          </view>
          <view class="hero-copy">
            <text class="hero-kicker">REMINDER SERVICE</text>
            <text class="hero-title">{{ permissionTitle }}</text>
            <text class="hero-note">{{ permissionDescription }}</text>
          </view>
        </view>
        <view class="hero-actions">
          <button class="hero-primary pressable" :disabled="permission === 'checking'" @tap="enableNotifications">
            <Check v-if="permission === 'granted'" :size="16" />
            <BellRing v-else :size="16" />
            <text>{{ permissionAction }}</text>
          </button>
          <button v-if="permission === 'granted'" class="hero-secondary pressable" @tap="testNotification">
            <Send :size="16" />
            <text>测试提醒</text>
          </button>
        </view>
      </view>

      <view class="fact-grid">
        <view class="fact-card">
          <view class="fact-icon"><Clock3 :size="17" /></view>
          <text class="fact-label">全天计划</text>
          <text class="fact-value">{{ ALL_DAY_REMINDER_TIME }}</text>
          <text class="fact-note">未指定时刻时提醒</text>
        </view>
        <view class="fact-card">
          <view class="fact-icon"><CalendarDays :size="17" /></view>
          <text class="fact-label">下一提醒</text>
          <text class="fact-value compact-value">{{ nextReminderText }}</text>
          <text class="fact-note">只统计未来计划</text>
        </view>
        <view class="fact-card wide">
          <view class="fact-icon"><Smartphone :size="17" /></view>
          <text class="fact-label">当前提醒方式</text>
          <text class="fact-value">{{ reminderMode }}</text>
          <text class="fact-note">{{ reminderModeNote }}</text>
        </view>
      </view>

      <StatusNotice
        v-if="actionError"
        tone="error"
        title="提醒服务没有完成这次操作"
        :message="actionError"
        closeable
        @close="actionError = ''"
      />
      <StatusNotice
        v-if="actionSuccess"
        tone="success"
        title="提醒服务已更新"
        :message="actionSuccess"
        closeable
        @close="actionSuccess = ''"
      />
      <StatusNotice
        v-if="loadError"
        tone="warning"
        title="计划列表没有完全同步"
        :message="loadError"
        action-text="重新加载"
        @action="loadPage"
      />

      <view class="section-block upcoming-section">
        <view class="section-head">
          <view>
            <text class="section-kicker">UPCOMING</text>
            <text class="section-title">即将提醒</text>
          </view>
          <text class="section-count">{{ upcomingPlans.length }} 项</text>
        </view>

        <view v-if="loading && !plans.length" class="plan-loading">
          <LoaderCircle :size="20" class="spin" />
          <text>正在读取待办计划</text>
        </view>
        <view v-else-if="upcomingPlans.length" class="upcoming-list">
          <view v-for="item in upcomingPlans" :key="item.record_id" class="upcoming-row">
            <view class="time-box">
              <text class="time-main">{{ item.timeLabel }}</text>
              <text class="time-date">{{ item.dateLabel }}</text>
            </view>
            <view class="upcoming-copy">
              <text class="upcoming-title">{{ item.content }}</text>
              <text class="upcoming-meta">{{ item.project || "未关联项目/企业" }} · {{ item.statusLabel }}</text>
            </view>
            <ChevronRight :size="16" class="upcoming-arrow" />
          </view>
        </view>
        <StatePanel
          v-else
          compact
          state="empty"
          title="暂时没有未来提醒"
          description="创建待办计划并为它选择日期和时间后，提醒会出现在这里。"
          action-text="去说计划"
          @action="openPlanReview"
        />
      </view>

      <view class="section-block schedule-section">
        <view class="section-head">
          <view>
            <text class="section-kicker">DAILY RHYTHM</text>
            <text class="section-title">固定提醒</text>
          </view>
          <text class="section-count">每天</text>
        </view>
        <view class="schedule-card">
          <view class="schedule-row">
            <view class="schedule-icon morning"><BellRing :size="17" /></view>
            <view class="schedule-copy">
              <text class="schedule-title">早上看一眼今天的安排</text>
              <text class="schedule-note">先确认最重要的三件事</text>
            </view>
            <text class="schedule-time">08:30</text>
          </view>
          <view class="schedule-row">
            <view class="schedule-icon evening"><CircleAlert :size="17" /></view>
            <view class="schedule-copy">
              <text class="schedule-title">傍晚收好今天的工作</text>
              <text class="schedule-note">确认完成情况，留下复盘</text>
            </view>
            <text class="schedule-time">17:30</text>
          </view>
        </view>
      </view>

      <view class="section-block boundary-card">
        <view class="boundary-icon"><ShieldCheck :size="20" /></view>
        <view class="boundary-copy">
          <text class="boundary-title">提醒边界说明</text>
          <text class="boundary-note">{{ boundaryText }}</text>
        </view>
      </view>

      <view class="scroll-space"></view>
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import {
  BellOff,
  BellRing,
  CalendarDays,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  LoaderCircle,
  RefreshCw,
  Send,
  ShieldCheck,
  Smartphone,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import StatePanel from "../../components/StatePanel.vue";
import StatusNotice from "../../components/StatusNotice.vue";
import { request } from "../../services/api";
import { getCachedRecords } from "../../services/localDb";
import {
  ALL_DAY_REMINDER_TIME,
  hasBackgroundReminderSupport,
  notificationPermission,
  requestNotificationPermission,
  schedulePlanReminder,
  showNotification,
} from "../../services/reminders";
import { ensureBound } from "../../services/session";

const plans = ref([]);
const permission = ref("checking");
const loading = ref(false);
const loadError = ref("");
const actionError = ref("");
const actionSuccess = ref("");

const permissionTone = computed(() => {
  if (permission.value === "granted") return "ready";
  if (permission.value === "checking") return "checking";
  if (permission.value === "unsupported") return "info";
  return "warning";
});
const permissionTitle = computed(() => {
  if (permission.value === "granted") return "提醒服务已开启";
  if (permission.value === "checking") return "正在检查提醒服务";
  if (permission.value === "unsupported") return "当前环境不能发系统通知";
  if (permission.value === "denied") return "系统通知被关闭了";
  return "提醒服务还没有开启";
});
const permissionDescription = computed(() => {
  if (permission.value === "granted") {
    return hasBackgroundReminderSupport()
      ? "计划会按日期和时间安排后台通知，到点提醒你。"
      : "网页打开时会在到点弹出提醒；安装 App 后可以获得后台通知。";
  }
  if (permission.value === "checking") return "正在读取当前设备的通知权限。";
  if (permission.value === "unsupported") return "计划仍然会保存，只是当前环境不能主动弹出系统通知。";
  if (permission.value === "denied") return "计划仍然会保存，但到点不会主动通知；请到系统设置中重新开启。";
  return "开启通知后，计划才能在到点时提醒你。";
});
const permissionAction = computed(() => {
  if (permission.value === "granted") return "同步已开启的提醒";
  if (permission.value === "unsupported") return "查看使用说明";
  if (permission.value === "denied") return "查看系统设置";
  return "开启提醒服务";
});
const reminderMode = computed(() => (hasBackgroundReminderSupport() ? "App 后台通知" : "网页前台提醒"));
const reminderModeNote = computed(() =>
  hasBackgroundReminderSupport()
    ? "关闭页面后仍可收到计划通知"
    : "请保持页面打开才能收到网页提醒",
);
const boundaryText = computed(() =>
  hasBackgroundReminderSupport()
    ? "App 会申请系统通知权限并创建提醒通道。若权限被关闭，计划仍会正常保存，但不会在到点时弹出通知。"
    : "普通网页只能在前台运行页面时安排提醒，无法保证关闭浏览器后的通知。安装 Android / iOS App 后可获得后台提醒能力。",
);
const upcomingPlans = computed(() => {
  const now = Date.now();
  return plans.value
    .filter((plan) => ![2, 3].includes(Number(plan.ext_field_5 ?? 0)))
    .map((plan) => {
      const time = plan.ext_field_4 || ALL_DAY_REMINDER_TIME;
      const trigger = new Date(`${plan.record_date}T${time}:00`).getTime();
      return { plan, trigger, time };
    })
    .filter((item) => Number.isFinite(item.trigger) && item.trigger > now)
    .sort((a, b) => a.trigger - b.trigger)
    .slice(0, 8)
    .map(({ plan, trigger, time }) => {
      const date = new Date(trigger);
      return {
        record_id: plan.record_id,
        content: String(plan.content || "未填写计划内容"),
        project: plan.related_project || "",
        timeLabel: time,
        dateLabel: `${date.getMonth() + 1} 月 ${date.getDate()} 日`,
        statusLabel: plan.ext_field_4 ? "指定时刻提醒" : "全天计划",
      };
    });
});
const nextReminderText = computed(() => {
  if (!upcomingPlans.value.length) return "暂无";
  const next = upcomingPlans.value[0];
  return `${next.dateLabel} ${next.timeLabel}`;
});

async function loadPage() {
  if (loading.value) return;
  loading.value = true;
  loadError.value = "";
  actionError.value = "";
  try {
    const [permissionResult, planResult] = await Promise.allSettled([
      notificationPermission(),
      request("/work-logs?record_type=待办计划&page_size=200"),
    ]);

    permission.value = permissionResult.status === "fulfilled"
      ? permissionResult.value
      : "unknown";
    if (permissionResult.status !== "fulfilled") {
      actionError.value = permissionResult.reason?.message || "无法读取通知权限状态。";
    }

    if (planResult.status === "fulfilled") {
      plans.value = planResult.value.items || [];
    } else {
      const cached = await getCachedRecords("work").catch(() => []);
      plans.value = cached.filter((item) => item.record_type === "待办计划");
      loadError.value = plans.value.length
        ? `${planResult.reason?.message || "计划服务暂时不可用"} 当前显示最近一次保存在本机的计划。`
        : planResult.reason?.message || "无法读取计划，请检查网络和资料库服务。";
    }

    if (permission.value === "granted") {
      await syncActiveReminders();
    }
  } finally {
    loading.value = false;
  }
}

async function enableNotifications() {
  actionError.value = "";
  actionSuccess.value = "";
  if (permission.value === "unsupported") {
    uni.showModal({
      title: "当前环境不能发系统通知",
      content: boundaryText.value,
      showCancel: false,
    });
    return;
  }
  if (permission.value === "denied") {
    uni.showModal({
      title: "请重新开启通知",
      content: "请到系统设置中找到当前浏览器或 Sayo Sense，允许通知后再回来同步。",
      showCancel: false,
    });
    return;
  }
  try {
    const result = await requestNotificationPermission();
    permission.value = result;
    if (result === "granted") {
      const resultCount = await syncActiveReminders();
      actionSuccess.value = resultCount
        ? `已同步 ${resultCount} 条未来计划提醒。`
        : "提醒权限已经开启，暂时没有新的未来计划。";
    } else if (result === "denied") {
      actionError.value = "通知权限没有开启。计划会保存，但到点不会主动通知。";
    } else if (result === "unsupported") {
      actionError.value = "当前运行环境不支持系统通知，请先使用支持通知的浏览器或安装 App。";
    } else {
      actionError.value = "系统没有返回通知权限状态，请稍后在系统设置中检查。";
    }
  } catch (error) {
    actionError.value = error.message || "提醒权限设置失败，请稍后重试。";
  }
}

async function syncActiveReminders() {
  const active = plans.value.filter((plan) => ![2, 3].includes(Number(plan.ext_field_5 ?? 0)));
  const outcomes = await Promise.allSettled(
    active.map((plan) => schedulePlanReminder(plan, { requestPermission: false })),
  );
  const failures = outcomes.filter((item) => item.status === "rejected");
  if (failures.length) {
    actionError.value = `有 ${failures.length} 条计划提醒没有同步成功，请检查权限后重试。`;
  }
  return outcomes.filter((item) => item.status === "fulfilled" && item.value).length;
}

async function testNotification() {
  actionError.value = "";
  try {
    const sent = await showNotification(
      "提醒服务测试",
      "看到这条通知，说明当前设备的提醒服务已经连通。",
      {},
    );
    if (sent) actionSuccess.value = "测试提醒已发送，请留意系统通知。";
    else actionError.value = "测试提醒没有发送成功，请检查系统通知权限。";
  } catch (error) {
    actionError.value = error.message || "测试提醒发送失败，请稍后重试。";
  }
}

function openPlanReview() {
  uni.navigateTo({ url: "/pages/plan-review/index?voice=1" });
}

onShow(() => {
  if (ensureBound()) loadPage();
});
</script>

<style scoped>
.reminders-page {
  height: 100vh;
  overflow: hidden;
}
.header-action {
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 6px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 650;
}
.reminders-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.service-hero {
  position: relative;
  margin: 4px 16px 0;
  overflow: hidden;
  padding: 18px;
  border: 1px solid #cfe2dd;
  border-radius: 12px;
  background: var(--ink);
  color: #ffffff;
  box-shadow: 0 12px 26px rgba(22, 34, 31, 0.16);
}
.service-hero.tone-warning {
  background: #263630;
}
.service-hero.tone-info {
  background: #25343a;
}
.hero-pattern {
  position: absolute;
  right: -48px;
  bottom: -78px;
  width: 180px;
  height: 180px;
  border: 1px solid rgba(150, 235, 215, 0.22);
  border-radius: 50%;
}
.hero-pattern::after {
  content: "";
  position: absolute;
  inset: 24px;
  border: 1px solid rgba(150, 235, 215, 0.12);
  border-radius: 50%;
}
.hero-head {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.hero-icon {
  width: 48px;
  height: 48px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(166, 240, 221, 0.3);
  border-radius: 50%;
  background: rgba(129, 225, 205, 0.1);
  color: #c4f8ea;
}
.tone-warning .hero-icon,
.tone-info .hero-icon {
  border-color: rgba(255, 211, 177, 0.22);
  color: #ffd3b1;
}
.hero-copy {
  flex: 1;
  min-width: 0;
}
.hero-kicker {
  display: block;
  color: #8ed8c8;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.1em;
}
.tone-warning .hero-kicker,
.tone-info .hero-kicker {
  color: #e9b99a;
}
.hero-title {
  display: block;
  margin-top: 6px;
  font-size: 20px;
  font-weight: 740;
  line-height: 27px;
}
.hero-note {
  display: block;
  max-width: 285px;
  margin-top: 5px;
  color: #b6cbc4;
  font-size: 12px;
  line-height: 19px;
}
.hero-actions {
  position: relative;
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
.hero-primary,
.hero-secondary {
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 13px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 650;
}
.hero-primary {
  background: #d5f4eb;
  color: #12382f;
}
.hero-secondary {
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.07);
  color: #e1f5ef;
}
.hero-primary[disabled] {
  opacity: 0.5;
}
.fact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 16px 0;
}
.fact-card {
  min-width: 0;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.fact-card.wide {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) auto;
  align-items: center;
  column-gap: 8px;
}
.fact-icon {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 7px;
  border-radius: 7px;
  background: var(--accent-soft);
  color: var(--accent);
}
.wide .fact-icon {
  grid-row: span 2;
  margin-bottom: 0;
}
.fact-label {
  display: block;
  color: var(--text-muted);
  font-size: 10px;
}
.fact-value {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: var(--ink);
  font-size: 15px;
  font-weight: 720;
  line-height: 21px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.compact-value {
  font-size: 13px;
}
.fact-note {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 15px;
}
.wide .fact-label,
.wide .fact-value,
.wide .fact-note {
  grid-column: 2;
}
.wide .fact-value {
  grid-row: 2;
  margin-top: 0;
}
.wide .fact-note {
  grid-column: 2;
  grid-row: 3;
}
.reminders-page :deep(.status-notice) {
  margin-left: 16px;
  margin-right: 16px;
}
.section-block {
  margin: 22px 16px 0;
}
.section-head {
  min-height: 41px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.section-kicker {
  display: block;
  margin-bottom: 3px;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.1em;
}
.section-title {
  display: block;
  color: var(--ink);
  font-size: 18px;
  font-weight: 730;
  line-height: 24px;
}
.section-count {
  color: var(--text-muted);
  font-size: 11px;
}
.upcoming-list,
.schedule-card {
  margin-top: 9px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.upcoming-row,
.schedule-row {
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-bottom: 1px solid var(--border);
}
.upcoming-row:last-child,
.schedule-row:last-child {
  border-bottom: 0;
}
.time-box {
  width: 54px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 7px 4px;
  border-radius: 7px;
  background: var(--surface-soft);
}
.time-main {
  color: var(--ink);
  font-size: 14px;
  font-weight: 720;
  line-height: 18px;
}
.time-date {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 9px;
  white-space: nowrap;
}
.upcoming-copy {
  min-width: 0;
  flex: 1;
}
.upcoming-title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
  line-height: 19px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.upcoming-meta {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upcoming-arrow {
  flex: none;
  color: var(--text-muted);
}
.plan-loading {
  min-height: 112px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 12px;
}
.schedule-icon {
  width: 35px;
  height: 35px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}
.schedule-icon.morning {
  background: var(--accent-soft);
  color: var(--accent);
}
.schedule-icon.evening {
  background: var(--warning-bg);
  color: var(--warning);
}
.schedule-copy {
  min-width: 0;
  flex: 1;
}
.schedule-title {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}
.schedule-note {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 11px;
}
.schedule-time {
  flex: none;
  color: var(--accent);
  font-size: 13px;
  font-weight: 700;
}
.boundary-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 13px;
  border: 1px solid #ead7c5;
  border-radius: 8px;
  background: #fffaf4;
}
.boundary-icon {
  width: 35px;
  height: 35px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--warning-bg);
  color: var(--warning);
}
.boundary-copy {
  min-width: 0;
}
.boundary-title {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}
.boundary-note {
  display: block;
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 18px;
}
.scroll-space {
  height: calc(24px + env(safe-area-inset-bottom));
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 360px) {
  .service-hero,
  .fact-grid,
  .section-block {
    margin-left: 12px;
    margin-right: 12px;
  }
  .reminders-page :deep(.status-notice) {
    margin-left: 12px;
    margin-right: 12px;
  }
  .hero-actions {
    flex-wrap: wrap;
  }
  .hero-primary,
  .hero-secondary {
    flex: 1;
    min-width: 132px;
  }
}
</style>
