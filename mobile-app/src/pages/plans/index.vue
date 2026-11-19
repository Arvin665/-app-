<template>
  <view class="plans-page app-page">
    <PageHeader title="计划与复盘" fallback="/pages/home/index">
      <template #actions>
        <view class="header-action pressable" @tap="openPlanVoice">
          <Plus :size="15" />
          <text>说计划</text>
        </view>
      </template>
    </PageHeader>

    <scroll-view class="plans-scroll" scroll-y>
      <view class="plan-hero">
        <view class="hero-meta">
          <text class="hero-kicker">DAILY RHYTHM</text>
          <text class="hero-date">{{ todayDisplay }}</text>
        </view>
        <text class="hero-title">把今天走稳，也把走过的路留住。</text>
        <text class="hero-note">语音安排时间，边做边记进展，晚上再统一回看。</text>

        <view class="hero-stats">
          <view class="hero-stat">
            <text class="stat-value">{{ todayPlans.length }}</text>
            <text class="stat-label">今日计划</text>
          </view>
          <view class="hero-stat">
            <text class="stat-value">{{ waitingCount }}</text>
            <text class="stat-label">等待推进</text>
          </view>
          <view class="hero-stat">
            <text class="stat-value">{{ completionRate }}<text class="stat-unit">%</text></text>
            <text class="stat-label">今日完成</text>
          </view>
        </view>

        <view class="voice-plan pressable" :class="{ recording: voice.active && voice.target === 'plan' }" @tap="openPlanVoice">
          <view class="voice-mark">
            <Square v-if="voice.active && voice.target === 'plan'" :size="19" fill="currentColor" />
            <Mic v-else :size="23" />
          </view>
          <view class="voice-copy">
            <text class="voice-title">连续说多项计划</text>
            <text class="voice-note">先拆分核对，再批量创建提醒</text>
          </view>
          <ChevronRight :size="18" class="voice-arrow" />
        </view>
      </view>

      <view
        v-if="todayPlans.length"
        class="archive-banner pressable"
        :class="{ locked: dailyLocked }"
        @tap="openDaily"
      >
        <view class="archive-icon">
          <Check v-if="dailyLocked" :size="18" />
          <Clock3 v-else :size="18" />
        </view>
        <view class="archive-copy">
          <text class="archive-title">{{ dailyLocked ? "今天的计划已经归档" : "收好今天的工作节奏" }}</text>
          <text class="archive-note">
            {{ dailyLocked ? "已生成每日复盘，可以随时回来查看。" : `还有 ${openTodayCount} 项没有完成，确认状态和心得后归档。` }}
          </text>
        </view>
        <text class="archive-action">{{ dailyLocked ? "查看" : "去确认" }}</text>
      </view>

      <view class="reminder-service" :class="`tone-${reminderTone}`">
        <view class="reminder-service-head">
          <view class="reminder-service-icon">
            <LoaderCircle v-if="reminderPermission === 'checking'" :size="18" class="spin" />
            <BellRing v-else-if="reminderPermission === 'granted'" :size="18" />
            <BellOff v-else :size="18" />
          </view>
          <view class="reminder-service-copy">
            <text class="reminder-service-title">{{ reminderTitle }}</text>
            <text class="reminder-service-note">{{ reminderDescription }}</text>
          </view>
          <view v-if="reminderActionText" class="reminder-service-action pressable" @tap="enableReminders">
            {{ reminderActionText }}
          </view>
        </view>
        <view class="reminder-facts">
          <view class="reminder-fact">
            <text class="fact-label">提醒方式</text>
            <text class="fact-value">{{ reminderModeLabel }}</text>
          </view>
          <view class="reminder-fact">
            <text class="fact-label">全天计划</text>
            <text class="fact-value">{{ ALL_DAY_REMINDER_TIME }}</text>
          </view>
          <view class="reminder-fact wide">
            <text class="fact-label">下一提醒</text>
            <text class="fact-value">{{ nextReminderText }}</text>
          </view>
        </view>
        <view class="reminder-service-footer">
          <text class="reminder-footer-note">每天 08:30 / 17:30 固定提醒</text>
          <view class="reminder-service-link pressable" @tap="openReminderService">
            <text>管理提醒</text>
            <ChevronRight :size="14" />
          </view>
        </view>
      </view>

      <StatusNotice
        v-if="reminderError"
        tone="error"
        title="提醒设置没有完成"
        :message="reminderError"
        action-text="重试"
        closeable
        @action="enableReminders"
        @close="reminderError = ''"
      />
      <StatusNotice
        v-if="actionError"
        tone="error"
        title="这项操作没有保存成功"
        :message="actionError"
        closeable
        @close="actionError = ''"
      />

      <StatusNotice
        v-if="plansError && plans.length"
        tone="warning"
        title="当前显示本机计划"
        :message="plansError"
        action-text="重新连接"
        @action="loadPlans"
      />
      <StatusNotice
        v-if="tab === 'records' && recordsError && records.length"
        tone="warning"
        title="当前显示本机记录"
        :message="recordsError"
        action-text="重新连接"
        @action="loadAll"
      />

      <view class="tab-switch">
        <view class="tab-item pressable" :class="{ active: tab === 'plans' }" @tap="switchTab('plans')">
          <CalendarDays :size="16" />
          <text>待办计划</text>
          <text v-if="tab === 'plans'" class="tab-count">{{ plans.length }}</text>
        </view>
        <view class="tab-item pressable" :class="{ active: tab === 'records' }" @tap="switchTab('records')">
          <History :size="16" />
          <text>工作记录</text>
          <text v-if="tab === 'records'" class="tab-count">{{ records.length }}</text>
        </view>
      </view>

      <template v-if="tab === 'plans'">
        <view v-if="activePlans.length" class="plan-section">
          <view class="section-head">
            <view>
              <text class="section-kicker">IN PROGRESS</text>
              <text class="section-title">待推进</text>
            </view>
            <text class="section-count">{{ activePlans.length }} 项</text>
          </view>

          <view class="plan-list">
            <view
              v-for="plan in activePlans"
              :key="plan.record_id"
              class="plan-card"
              :class="`status-${Number(plan.ext_field_5) || 0}`"
            >
              <view class="plan-rail">
                <text class="plan-time">{{ plan.ext_field_4 || "全天" }}</text>
                <view class="rail-line"></view>
                <text class="plan-status">{{ statusShort(plan) }}</text>
              </view>

              <view class="plan-main">
                <view class="plan-title-line pressable" @tap="openDetail(plan)">
                  <text class="plan-content">{{ plan.content || "未填写计划内容" }}</text>
                  <ChevronRight :size="16" class="plan-arrow" />
                </view>
                <view class="plan-meta">
                  <text>{{ formatPlanDate(plan.record_date) }}</text>
                  <text v-if="plan.related_project" class="meta-project">{{ plan.related_project }}</text>
                </view>
                <view class="reminder-line" :class="`tone-${reminderMeta(plan).tone}`">
                  <BellRing v-if="reminderMeta(plan).tone === 'active'" :size="13" />
                  <BellOff v-else :size="13" />
                  <text>{{ reminderMeta(plan).label }}</text>
                </view>
                <text v-if="plan.ext_field_1" class="progress-note">{{ latestNote(plan.ext_field_1) }}</text>

                <view v-if="!dailyLocked && isCurrentDay(plan.record_date)" class="status-grid">
                  <view
                    v-for="item in statuses"
                    :key="item.value"
                    class="status-pill pressable"
                    :class="{ selected: Number(plan.ext_field_5 ?? 0) === item.value }"
                    @tap="selectPlanStatus(plan, item)"
                  >
                    {{ item.short }}
                  </view>
                </view>
                <view v-if="!dailyLocked" class="plan-actions">
                  <view class="text-action pressable" @tap="openProgress(plan)">
                    <Mic :size="13" />
                    <text>说进展</text>
                  </view>
                  <view class="text-action pressable" @tap="openPostpone(plan)">
                    <Clock3 :size="13" />
                    <text>推迟</text>
                  </view>
                  <view class="text-action subtle pressable" @tap="openDetail(plan)">
                    <text>详情</text>
                    <ChevronRight :size="13" />
                  </view>
                </view>
              </view>
            </view>
          </view>
        </view>

        <view v-if="completedPlans.length" class="plan-section completed-section">
          <view class="section-head">
            <view>
              <text class="section-kicker">DONE</text>
              <text class="section-title">已做好</text>
            </view>
            <text class="section-count">{{ completedPlans.length }} 项</text>
          </view>

          <view class="completed-list">
            <view
              v-for="plan in completedPlans"
              :key="plan.record_id"
              class="completed-row pressable"
              @tap="openDetail(plan)"
            >
              <view class="done-mark"><Check :size="14" /></view>
              <view class="done-main">
                <text class="done-title">{{ plan.content || "已完成计划" }}</text>
                <text class="done-meta">{{ formatPlanDate(plan.record_date) }} · {{ plan.ext_field_4 || "全天" }}</text>
              </view>
              <ChevronRight :size="15" class="done-arrow" />
            </view>
          </view>
        </view>

        <StatePanel
          v-if="loadingPlans && !plans.length"
          state="loading"
          title="正在整理计划"
          description="今天的安排和你留下的计划正在同步。"
        />
        <StatePanel
          v-else-if="plansError && !plans.length"
          state="error"
          title="计划暂时没有加载出来"
          :description="plansError"
          action-text="重新加载"
          @action="loadPlans"
        />
        <StatePanel
          v-else-if="!plans.length"
          state="empty"
          title="还没有待办计划"
          description="说出事项和时间，App 会先拆成清单，核对后再创建提醒。"
          action-text="说第一条计划"
          @action="openPlanVoice"
        />
      </template>

      <template v-else>
        <view class="section-head records-heading">
          <view>
            <text class="section-kicker">WORK NOTES</text>
            <text class="section-title">工作记录</text>
          </view>
          <view class="record-entry pressable" @tap="openWorkEntry">
            <Plus :size="14" />
            <text>记一条</text>
          </view>
        </view>

        <view v-if="records.length" class="record-list">
          <view
            v-for="record in records"
            :key="record.record_id"
            class="record-card pressable"
            @tap="openDetail(record)"
          >
            <view class="record-date-box">
              <text class="record-day">{{ dayOf(record.record_date) }}</text>
              <text class="record-month">{{ monthOf(record.record_date) }}</text>
            </view>
            <view class="record-main">
              <view class="record-head">
                <text class="record-type">{{ record.record_type || "工作记录" }}</text>
                <text v-if="record.is_shared" class="shared-tag">团队共享</text>
              </view>
              <text class="record-content">{{ record.content || record.todo_items || "未填写正文" }}</text>
              <text v-if="record.related_project" class="record-project">{{ record.related_project }}</text>
            </view>
            <ChevronRight :size="15" class="record-arrow" />
          </view>
        </view>
        <StatePanel
          v-if="loadingRecords && !records.length"
          state="loading"
          title="正在翻阅工作记录"
          description="已经收好的进展和材料正在同步。"
        />
        <StatePanel
          v-else-if="recordsError && !records.length"
          state="error"
          title="工作记录暂时没有加载出来"
          :description="recordsError"
          action-text="重新加载"
          @action="loadAll"
        />
        <StatePanel
          v-else-if="!records.length"
          state="empty"
          title="还没有工作记录"
          description="把今天做过、看到或准备继续做的事说出来。"
          action-text="说一条工作记录"
          @action="openWorkEntry"
        />
      </template>

      <view class="scroll-space"></view>
    </scroll-view>

    <AppTabBar active="plans" />

    <view v-if="noteModal.visible" class="sheet-mask" @tap="closeNote">
      <view class="bottom-sheet safe-bottom" @tap.stop>
        <view class="sheet-handle"></view>
        <view class="sheet-head">
          <view>
            <text class="sheet-kicker">{{ noteModal.status === 2 ? "COMPLETE" : "PROGRESS" }}</text>
            <text class="sheet-title">{{ noteModal.title }}</text>
          </view>
          <view class="sheet-close pressable" @tap="closeNote"><X :size="18" /></view>
        </view>

        <view class="sheet-plan">
          <text class="sheet-plan-time">{{ noteModal.plan?.ext_field_4 || "全天" }}</text>
          <text class="sheet-plan-content">{{ noteModal.plan?.content }}</text>
        </view>

        <textarea
          v-model="noteModal.note"
          class="sheet-textarea"
          maxlength="500"
          auto-height
          :placeholder="noteModal.placeholder"
        />
        <text v-if="voice.active && voice.target === 'note'" class="voice-live">{{ voice.interim || (voice.phase === "stopping" ? "正在收尾，请稍等..." : "正在听，再按一下结束...") }}</text>

        <view class="voice-input-row">
          <view class="voice-input-button pressable" :class="{ recording: voice.active && voice.target === 'note', stopping: voice.active && voice.target === 'note' && voice.phase === 'stopping' }" @tap="toggleVoice('note')">
            <Square v-if="voice.active && voice.target === 'note'" :size="15" fill="currentColor" />
            <Mic v-else :size="17" />
            <text>{{ voice.active && voice.target === "note" ? (voice.phase === "stopping" ? "收尾中" : "停止") : "语音说进展" }}</text>
          </view>
          <text class="voice-tip">说错也可以继续补充</text>
        </view>

        <button class="sheet-primary pressable" @tap="submitStatus">
          <Check :size="18" />
          <text>保存状态与进展</text>
        </button>
      </view>
    </view>

    <view v-if="postpone.visible" class="sheet-mask" @tap="closePostpone">
      <view class="bottom-sheet safe-bottom" @tap.stop>
        <view class="sheet-handle"></view>
        <view class="sheet-head">
          <view>
            <text class="sheet-kicker">RESCHEDULE</text>
            <text class="sheet-title">推迟计划</text>
          </view>
          <view class="sheet-close pressable" @tap="closePostpone"><X :size="18" /></view>
        </view>

        <view class="sheet-plan">
          <text class="sheet-plan-time">{{ postpone.plan?.record_date }} {{ postpone.plan?.ext_field_4 || "全天" }}</text>
          <text class="sheet-plan-content">{{ postpone.plan?.content }}</text>
        </view>

        <view class="postpone-grid">
          <picker mode="date" :value="postpone.date" @change="postpone.date = $event.detail.value">
            <view class="picker-card">
              <text class="picker-label">新日期</text>
              <text class="picker-value">{{ postpone.date }}</text>
            </view>
          </picker>
          <picker mode="time" :value="postpone.time || '09:00'" @change="postpone.time = $event.detail.value">
            <view class="picker-card">
              <text class="picker-label">新时间</text>
              <text class="picker-value">{{ postpone.time || "选择时间" }}</text>
            </view>
          </picker>
        </view>

        <textarea
          v-model="postpone.reason"
          class="sheet-textarea compact-textarea"
          maxlength="500"
          auto-height
          placeholder="说明为什么推迟，之后回看会更清楚"
        />
        <text v-if="voice.active && voice.target === 'postpone'" class="voice-live">{{ voice.interim || (voice.phase === "stopping" ? "正在收尾，请稍等..." : "正在听日期、时间和原因，再按一下结束...") }}</text>

        <view class="voice-input-row">
          <view class="voice-input-button pressable" :class="{ recording: voice.active && voice.target === 'postpone', stopping: voice.active && voice.target === 'postpone' && voice.phase === 'stopping' }" @tap="toggleVoice('postpone')">
            <Square v-if="voice.active && voice.target === 'postpone'" :size="15" fill="currentColor" />
            <Mic v-else :size="17" />
            <text>{{ voice.active && voice.target === "postpone" ? (voice.phase === "stopping" ? "收尾中" : "停止") : "说新安排" }}</text>
          </view>
          <text class="voice-tip">日期、时间和原因一起说</text>
        </view>

        <view class="sheet-actions">
          <button class="sheet-secondary pressable" @tap="closePostpone">取消</button>
          <button class="sheet-primary flex-primary pressable" @tap="submitPostpone">
            <Clock3 :size="17" />
            <text>确认推迟</text>
          </button>
        </view>
      </view>
    </view>

    <DailyConfirmModal
      :visible="dailyModal"
      :plans="todayPlans"
      :record-date="today"
      :saving="archiving"
      :locked="dailyLocked"
      @close="dailyModal = false; rememberDismiss()"
      @archive="archiveDaily"
      @update-plan="updateFromDaily"
    />
  </view>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { onLoad, onPullDownRefresh, onShow, onUnload } from "@dcloudio/uni-app";
import {
  CalendarDays,
  BellOff,
  BellRing,
  Check,
  ChevronRight,
  Clock3,
  History,
  LoaderCircle,
  Mic,
  Plus,
  Square,
  X,
} from "@lucide/vue";
import AppTabBar from "../../components/AppTabBar.vue";
import DailyConfirmModal from "../../components/DailyConfirmModal.vue";
import PageHeader from "../../components/PageHeader.vue";
import StatePanel from "../../components/StatePanel.vue";
import StatusNotice from "../../components/StatusNotice.vue";
import { localDate, normalizeRecordPayload } from "../../data/modules";
import { isNetworkError, request } from "../../services/api";
import {
  cacheRecords,
  enqueueOffline,
  getCachedRecords,
} from "../../services/localDb";
import {
  cancelPlanReminder,
  ALL_DAY_REMINDER_TIME,
  hasBackgroundReminderSupport,
  notificationPermission,
  requestNotificationPermission,
  schedulePlanReminder,
} from "../../services/reminders";
import { dictationAvailable, startDictation } from "../../services/voice";

const tab = ref("plans");
const records = ref([]);
const plans = ref([]);
const todayPlans = ref([]);
const loadingRecords = ref(false);
const loadingPlans = ref(false);
const recordsError = ref("");
const plansError = ref("");
const reminderError = ref("");
const actionError = ref("");
const reminderPermission = ref("checking");
const dailyLocked = ref(false);
const dailyModal = ref(false);
const archiving = ref(false);
const today = localDate();
const todayKey = `daily-dismissed-${today}`;
const voice = reactive({ active: false, phase: "idle", target: "", interim: "" });
const loading = computed(() => loadingRecords.value || loadingPlans.value);
let clock = null;
let voiceSession = null;

const statuses = [
  { value: 0, label: "未做", short: "未做" },
  { value: 1, label: "正在做", short: "进行中" },
  { value: 2, label: "已做好", short: "已做好" },
  { value: 3, label: "计划搁置", short: "搁置" },
];
const statusMap = { 0: "未做", 1: "正在做", 2: "已做好", 3: "计划搁置" };

const noteModal = reactive({
  visible: false,
  plan: null,
  status: 1,
  title: "",
  placeholder: "",
  note: "",
});
const postpone = reactive({
  visible: false,
  plan: null,
  date: today,
  time: "09:00",
  reason: "",
});

const activePlans = computed(() =>
  plans.value
    .filter((item) => Number(item.ext_field_5 ?? 0) !== 2)
    .sort((a, b) => `${a.record_date}${a.ext_field_4 || ""}`.localeCompare(`${b.record_date}${b.ext_field_4 || ""}`)),
);
const completedPlans = computed(() =>
  plans.value
    .filter((item) => Number(item.ext_field_5 ?? 0) === 2)
    .sort((a, b) => `${b.record_date}${b.ext_field_4 || ""}`.localeCompare(`${a.record_date}${a.ext_field_4 || ""}`)),
);
const waitingCount = computed(() => plans.value.filter((item) => [0, 1].includes(Number(item.ext_field_5 ?? 0))).length);
const openTodayCount = computed(
  () => todayPlans.value.filter((item) => Number(item.ext_field_5 ?? 0) !== 2).length,
);
const completionRate = computed(() => {
  if (!todayPlans.value.length) return 0;
  const completed = todayPlans.value.filter((item) => Number(item.ext_field_5 ?? 0) === 2).length;
  return Math.round((completed / todayPlans.value.length) * 100);
});
const todayDisplay = computed(() => {
  const current = new Date();
  const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  return `${current.getMonth() + 1} 月 ${current.getDate()} 日 · ${weekdays[current.getDay()]}`;
});
const reminderTone = computed(() => {
  if (reminderPermission.value === "granted") return "ready";
  if (reminderPermission.value === "checking") return "checking";
  if (reminderPermission.value === "unsupported") return "info";
  return "warning";
});
const reminderTitle = computed(() => {
  if (reminderPermission.value === "checking") return "正在检查提醒服务";
  if (reminderPermission.value === "granted") return hasBackgroundReminderSupport() ? "后台提醒已开启" : "网页提醒已开启";
  if (reminderPermission.value === "unsupported") return "当前环境不支持系统提醒";
  return "提醒服务还没有开启";
});
const reminderDescription = computed(() => {
  if (reminderPermission.value === "checking") return "正在读取系统通知权限";
  if (reminderPermission.value === "granted") {
    return hasBackgroundReminderSupport()
      ? `系统通知可用，未指定时刻按 ${ALL_DAY_REMINDER_TIME} 提醒。`
      : `网页打开时会提醒；安装 App 后可后台通知。未指定时刻按 ${ALL_DAY_REMINDER_TIME} 提醒。`;
  }
  if (reminderPermission.value === "unsupported") return "计划仍会保存，但当前环境无法弹出系统通知。";
  return `计划会正常保存，但到点不会主动通知。未指定时刻默认按 ${ALL_DAY_REMINDER_TIME} 提醒。`;
});
const reminderActionText = computed(() => {
  if (reminderPermission.value === "checking" || reminderPermission.value === "unsupported") return "";
  if (reminderPermission.value === "granted") return "同步提醒";
  return reminderPermission.value === "denied" ? "查看设置" : "开启提醒";
});
const reminderModeLabel = computed(() =>
  hasBackgroundReminderSupport() ? "App 后台通知" : "网页前台提醒",
);
const nextReminderText = computed(() => {
  const now = Date.now();
  const next = plans.value
    .filter((plan) => ![2, 3].includes(Number(plan.ext_field_5 ?? 0)))
    .map((plan) => ({
      plan,
      trigger: new Date(`${plan.record_date}T${plan.ext_field_4 || ALL_DAY_REMINDER_TIME}:00`).getTime(),
    }))
    .filter((item) => Number.isFinite(item.trigger) && item.trigger > now)
    .sort((a, b) => a.trigger - b.trigger)[0];
  if (!next) return "暂无未来提醒";
  const date = new Date(next.trigger);
  const dateLabel = `${date.getMonth() + 1} 月 ${date.getDate()} 日 ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  return `${dateLabel} · ${String(next.plan.content || "待办计划").slice(0, 16)}`;
});

async function refreshReminderPermission() {
  reminderPermission.value = await notificationPermission().catch(() => "unknown");
}

async function rescheduleActiveReminders() {
  const active = plans.value.filter((plan) => ![2, 3].includes(Number(plan.ext_field_5 ?? 0)));
  const outcomes = await Promise.allSettled(
    active.map((plan) => schedulePlanReminder(plan, { requestPermission: false })),
  );
  return {
    scheduled: outcomes.filter((item) => item.status === "fulfilled" && item.value).length,
    failed: outcomes.filter((item) => item.status === "rejected").length,
  };
}

async function enableReminders() {
  if (reminderPermission.value === "checking") return;
  reminderError.value = "";
  if (reminderPermission.value === "unsupported") {
    uni.showModal({
      title: "当前环境不支持系统提醒",
      content: "网页端只能在页面打开时提醒。安装 App 后可获得 Android / iOS 后台通知。",
      showCancel: false,
    });
    return;
  }
  try {
    if (reminderPermission.value === "granted") {
      const result = await rescheduleActiveReminders();
      if (result.failed) {
        reminderError.value = `有 ${result.failed} 条提醒没有同步成功，请检查系统通知权限后重试。`;
        return;
      }
      uni.showToast({ title: "提醒已重新同步", icon: "success" });
      return;
    }
    const result = await requestNotificationPermission();
    reminderPermission.value = result;
    if (result === "granted") {
      const rescheduled = await rescheduleActiveReminders();
      if (rescheduled.failed) reminderError.value = `提醒权限已开启，但有 ${rescheduled.failed} 条提醒没有同步成功。`;
      else uni.showToast({ title: "提醒服务已开启", icon: "success" });
      return;
    }
    if (result === "unknown") {
      reminderError.value = "系统没有返回通知权限状态，请稍后重试或到系统设置中检查。";
      return;
    }
    uni.showModal({
      title: "需要开启通知权限",
      content: "请在系统设置中找到当前浏览器或商办信息资产库，开启通知权限后再回来同步提醒。",
      showCancel: false,
    });
  } catch (error) {
    reminderError.value = error.message || "提醒服务暂时没有设置成功，请稍后重试。";
  }
}

function reminderMeta(plan) {
  const status = Number(plan.ext_field_5 ?? 0);
  if ([2, 3].includes(status)) return { label: "计划已结束，提醒已取消", tone: "muted" };
  if (reminderPermission.value !== "granted") return { label: "系统提醒未开启", tone: "warning" };
  const time = plan.ext_field_4 || ALL_DAY_REMINDER_TIME;
  const trigger = new Date(`${plan.record_date}T${time}:00`).getTime();
  if (!trigger || trigger <= Date.now()) return { label: "提醒时间已过", tone: "muted" };
  const dateLabel = plan.record_date === today ? "今天" : formatPlanDate(plan.record_date);
  const timeLabel = plan.ext_field_4 ? plan.ext_field_4 : `${ALL_DAY_REMINDER_TIME}（全天）`;
  return { label: `${dateLabel} ${timeLabel} 提醒`, tone: "active" };
}

async function loadAll() {
  if (loadingRecords.value) return;
  loadingRecords.value = true;
  try {
    const result = await request("/work-logs?page_size=500");
    records.value = result.items || [];
    recordsError.value = "";
    await cacheRecords("work", records.value, new Date().toISOString());
  } catch (error) {
    records.value = await getCachedRecords("work");
    recordsError.value = records.value.length
      ? `${error.message || "服务暂时不可用"} 当前展示最近一次保存在本机的记录。`
      : error.message || "无法读取工作记录，请检查网络和资料库服务。";
  } finally {
    loadingRecords.value = false;
  }
}

async function loadPlans() {
  if (loadingPlans.value) return;
  loadingPlans.value = true;
  try {
    const [planResult, todayResult] = await Promise.all([
      request("/work-logs?record_type=待办计划&page_size=500"),
      request(`/work-logs/plans?record_date=${today}`),
    ]);
    plans.value = planResult.items || [];
    todayPlans.value = todayResult.items || [];
    dailyLocked.value = Boolean(todayResult.locked);
    plansError.value = "";
    plans.value.forEach((plan) => schedulePlanReminder(plan));
  } catch (error) {
    const cached = await getCachedRecords("work");
    plans.value = cached.filter((item) => item.record_type === "待办计划");
    todayPlans.value = plans.value.filter((item) => item.record_date === today);
    plansError.value = plans.value.length
      ? `${error.message || "服务暂时不可用"} 当前展示最近一次保存在本机的计划。`
      : error.message || "无法读取计划，请检查网络和资料库服务。";
  } finally {
    loadingPlans.value = false;
    maybeOpenDaily();
  }
}

function switchTab(next) {
  tab.value = next;
  if (next === "records" && !records.value.length) loadAll();
}

function maybeOpenDaily() {
  const current = new Date();
  const after = current.getHours() > 17 || (current.getHours() === 17 && current.getMinutes() >= 30);
  const dismissed = uni.getStorageSync(todayKey);
  if (after && todayPlans.value.length && !dailyLocked.value && !dismissed) dailyModal.value = true;
}

function openDaily() {
  if (!todayPlans.value.length) {
    uni.showToast({ title: "今天还没有计划", icon: "none" });
    return;
  }
  dailyModal.value = true;
}

function rememberDismiss() {
  uni.setStorageSync(todayKey, true);
}

function openPlanVoice() {
  uni.navigateTo({ url: "/pages/plan-review/index?voice=1" });
}

function openReminderService() {
  uni.navigateTo({ url: "/pages/reminders/index" });
}

function openWorkEntry() {
  uni.navigateTo({ url: "/pages/entry/index?module=work&voice=1" });
}

function openDetail(record) {
  uni.navigateTo({ url: `/pages/detail/index?module=work&id=${record.record_id}` });
}

function selectPlanStatus(plan, item) {
  if (dailyLocked.value && item.value !== Number(plan.ext_field_5 ?? 0)) {
    uni.showToast({ title: "今日计划已归档锁定", icon: "none" });
    return;
  }
  if (item.value === 0) {
    submitPlanStatus(plan, 0, "");
    return;
  }
  openStatusSheet(plan, item);
}

function openProgress(plan) {
  openStatusSheet(plan, statuses[1]);
}

function openStatusSheet(plan, item) {
  abortVoice();
  noteModal.visible = true;
  noteModal.plan = plan;
  noteModal.status = item.value;
  noteModal.title = item.value === 2 ? "标记已完成" : item.value === 3 ? "说明搁置原因" : "记录当前进展";
  noteModal.placeholder =
    item.value === 1
      ? "说说做到哪一步、下一步是什么"
      : item.value === 2
        ? "说说完成情况，或这条计划带来的判断"
        : "说说为什么先搁置，之后什么条件下继续";
  noteModal.note = "";
}

function closeNote() {
  noteModal.visible = false;
  noteModal.plan = null;
  noteModal.note = "";
  abortVoice();
}

async function submitStatus() {
  if (!noteModal.plan) return;
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
  const stamp = new Date().toLocaleString("zh-CN", { hour12: false });
  const line = `[${stamp}] ${statusMap[status]}：${note}`;
  return {
    ...plan,
    ext_field_5: status,
    ext_field_1: note ? `${plan.ext_field_1 || ""}\n${line}`.trim() : plan.ext_field_1,
  };
}

async function submitPlanStatus(plan, status, note) {
  actionError.value = "";
  try {
    let updated;
    try {
      updated = await request(`/work-logs/${plan.record_id}/status`, {
        method: "POST",
        data: { status, note },
      });
    } catch (error) {
      if (!isNetworkError(error)) throw error;
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
    actionError.value = error.message || "状态更新失败，请检查网络后重试。";
  }
}

function replacePlan(updated) {
  const merge = (item) => (item.record_id === updated.record_id ? { ...item, ...updated } : item);
  plans.value = plans.value.map(merge);
  todayPlans.value = todayPlans.value.map(merge);
}

async function updateFromDaily({ plan, status, note }) {
  await submitPlanStatus(plan, status, note);
}

function openPostpone(plan) {
  abortVoice();
  postpone.visible = true;
  postpone.plan = plan;
  postpone.date = plan.record_date || today;
  postpone.time = plan.ext_field_4 || "09:00";
  postpone.reason = "";
}

function closePostpone() {
  postpone.visible = false;
  postpone.plan = null;
  postpone.reason = "";
  abortVoice();
}

async function submitPostpone() {
  if (!postpone.plan) return;
  if (!postpone.reason.trim()) {
    uni.showToast({ title: "请说明推迟原因", icon: "none" });
    return;
  }
  actionError.value = "";
  const plan = postpone.plan;
  const newDate = postpone.date;
  const newTime = postpone.time;
  const reason = postpone.reason.trim();
  let history = [];
  try {
    history = plan.ext_field_2 ? JSON.parse(plan.ext_field_2) : [];
  } catch (error) {
    history = [];
  }
  history.push({
    from_date: plan.record_date,
    from_time: plan.ext_field_4,
    to_date: newDate,
    to_time: newTime,
    reason,
    postponed_at: new Date().toISOString(),
  });
  const optimistic = {
    ...plan,
    record_date: newDate,
    ext_field_4: newTime,
    ext_field_2: JSON.stringify(history),
  };
  try {
    let updated;
    try {
      updated = await request(`/work-logs/${plan.record_id}/postpone`, {
        method: "POST",
        data: { new_date: newDate, new_time: newTime, reason },
      });
    } catch (error) {
      if (!isNetworkError(error)) throw error;
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
    await loadPlans();
    uni.showToast({ title: "计划已推迟", icon: "success" });
  } catch (error) {
    actionError.value = error.message || "推迟失败，请检查网络后重试。";
  }
}

async function archiveDaily(insight) {
  if (!todayPlans.value.length) {
    uni.showToast({ title: "今天没有计划可归档", icon: "none" });
    return;
  }
  if (dailyLocked.value) {
    uni.showToast({ title: "今日计划已经归档", icon: "none" });
    return;
  }
  actionError.value = "";
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
    actionError.value = error.message || "归档失败，请联网后重试。";
  } finally {
    archiving.value = false;
  }
}

function toggleVoice(target) {
  if (voice.active) {
    stopVoice();
    return;
  }
  if (!dictationAvailable()) {
    uni.showModal({
      title: "当前环境没有语音识别",
      content: "请检查麦克风权限和资料库服务连接。你仍然可以直接输入文字。",
      showCancel: false,
    });
    return;
  }
  voice.active = true;
  voice.phase = "listening";
  voice.target = target;
  voice.interim = "";
  voiceSession = startDictation({
    continuous: false,
    onStateChange: (state) => {
      if (voice.target === target) voice.phase = state;
    },
    onInterim: (text) => {
      voice.interim = text;
    },
    onFinal: (text) => {
      if (text.trim()) applyVoiceText(target, text.trim());
    },
    onError: (error) => {
      uni.showToast({ title: error.message || "语音识别暂不可用", icon: "none" });
    },
    onEnd: () => {
      voice.active = false;
      voice.phase = "idle";
      voice.target = "";
      voice.interim = "";
      voiceSession = null;
    },
  });
  if (!voiceSession) {
    voice.active = false;
    voice.phase = "idle";
    voice.target = "";
  }
}

async function stopVoice() {
  const session = voiceSession;
  if (!session) {
    voice.active = false;
    voice.phase = "idle";
    voice.target = "";
    voice.interim = "";
    return null;
  }
  voice.phase = "stopping";
  const result = await session.stop?.();
  if (voiceSession === session) voiceSession = null;
  return result;
}

function abortVoice() {
  if (voiceSession) {
    voiceSession.abort?.();
    return;
  }
  voice.active = false;
  voice.phase = "idle";
  voice.target = "";
  voice.interim = "";
}

function appendDictation(current, text) {
  const value = String(current || "").trim();
  if (!value) return text;
  return `${value}${/[。！？!?]$/.test(value) ? "" : "。"}${text}`;
}

async function applyVoiceText(target, text) {
  if (target === "note" && noteModal.visible) {
    noteModal.note = appendDictation(noteModal.note, text);
    return;
  }
  if (target === "postpone" && postpone.visible) {
    postpone.reason = appendDictation(postpone.reason, text);
    try {
      const [dateResult, timeResult] = await Promise.all([
        request("/ai/parse-field", {
          method: "POST",
          data: { module: "work", field: "record_date", text },
        }),
        request("/ai/parse-field", {
          method: "POST",
          data: { module: "work", field: "ext_field_4", text },
        }),
      ]);
      if (dateResult.value) postpone.date = dateResult.value;
      if (timeResult.value) postpone.time = timeResult.value;
      if (dateResult.value || timeResult.value) {
        uni.showToast({ title: "日期和时间已识别，请核对", icon: "none" });
      }
    } catch (error) {
      uni.showToast({ title: "原因已记录，日期时间请手动核对", icon: "none" });
    }
  }
}

function statusShort(plan) {
  return statusMap[Number(plan.ext_field_5 ?? 0)] || "未做";
}

function latestNote(value) {
  const lines = String(value || "").split("\n").filter(Boolean);
  return lines[lines.length - 1] || "";
}

function formatPlanDate(value) {
  if (!value) return "日期待补";
  if (value === today) return "今天";
  return String(value).slice(5).replace("-", " 月 ") + " 日";
}

function isCurrentDay(value) {
  return value === today;
}

function dayOf(value) {
  return String(value || "").slice(8, 10) || "—";
}

function monthOf(value) {
  return String(value || "").slice(5, 7) ? `${String(value).slice(5, 7)} 月` : "待补";
}

onLoad(() => {
  clock = setInterval(() => {
    maybeOpenDaily();
  }, 30000);
});

onShow(() => {
  loadPlans();
  refreshReminderPermission();
  if (!records.value.length) loadAll();
  setTimeout(maybeOpenDaily, 600);
});

onPullDownRefresh(async () => {
  await Promise.all([loadAll(), loadPlans()]);
  uni.stopPullDownRefresh();
});

onUnload(() => {
  if (clock) clearInterval(clock);
  voiceSession?.abort?.();
});
</script>

<style scoped>
.plans-page {
  height: 100vh;
  overflow: hidden;
}
.header-action {
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 0 7px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 650;
}
.plans-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.plan-hero {
  margin: 4px 16px 0;
  padding: 18px;
  border: 1px solid #cfe2dd;
  border-radius: 12px;
  background: linear-gradient(145deg, #f7fffc 0%, #ffffff 72%);
}
.hero-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.hero-kicker,
.section-kicker,
.sheet-kicker {
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.11em;
}
.hero-date {
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 600;
}
.hero-title {
  display: block;
  max-width: 310px;
  margin-top: 15px;
  color: var(--ink);
  font-size: 24px;
  font-weight: 760;
  line-height: 32px;
}
.hero-note {
  display: block;
  max-width: 310px;
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 18px;
}
.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 17px;
  padding: 12px 0;
  border-top: 1px solid rgba(28, 40, 37, 0.08);
  border-bottom: 1px solid rgba(28, 40, 37, 0.08);
}
.hero-stat {
  min-width: 0;
  padding-left: 12px;
  border-left: 1px solid rgba(28, 40, 37, 0.08);
}
.hero-stat:first-child {
  padding-left: 0;
  border-left: 0;
}
.stat-value {
  display: block;
  color: var(--ink);
  font-size: 23px;
  font-weight: 760;
  line-height: 27px;
}
.stat-unit {
  margin-left: 1px;
  font-size: 11px;
}
.stat-label {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 9px;
}
.voice-plan {
  min-height: 70px;
  display: flex;
  align-items: center;
  gap: 11px;
  margin-top: 14px;
  padding: 12px;
  border-radius: 9px;
  background: var(--ink);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(22, 34, 31, 0.15);
}
.voice-plan.recording {
  background: #123e35;
  box-shadow: 0 0 0 4px rgba(11, 117, 101, 0.12), 0 12px 26px rgba(22, 34, 31, 0.18);
}
.voice-mark {
  width: 43px;
  height: 43px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(150, 235, 215, 0.35);
  border-radius: 50%;
  background: rgba(128, 224, 204, 0.11);
  color: #c4f8ea;
}
.voice-copy {
  flex: 1;
  min-width: 0;
}
.voice-title {
  display: block;
  font-size: 14px;
  font-weight: 700;
}
.voice-note {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: #b5cbc4;
  font-size: 9px;
  line-height: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.voice-arrow {
  flex: none;
  color: #a8cbc2;
}
.reminder-service {
  display: block;
  margin: 12px 16px 0;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.reminder-service.tone-ready {
  border-color: #cfe5df;
  background: #f3faf7;
}
.reminder-service.tone-warning {
  border-color: #ead7c5;
  background: #fffaf4;
}
.reminder-service-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.reminder-service-icon {
  width: 34px;
  height: 34px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--accent-soft);
  color: var(--accent);
}
.tone-warning .reminder-service-icon {
  background: var(--warning-bg);
  color: var(--warning);
}
.tone-info .reminder-service-icon {
  background: var(--info-bg);
  color: var(--info);
}
.reminder-service-copy {
  min-width: 0;
  flex: 1;
}
.reminder-service-title {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}
.reminder-service-note {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 17px;
}
.reminder-service-action {
  min-height: 32px;
  flex: none;
  display: flex;
  align-items: center;
  padding: 0 9px;
  border: 1px solid currentColor;
  border-radius: 7px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 650;
}
.reminder-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.reminder-fact {
  min-width: 0;
  padding: 8px 9px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.62);
}
.reminder-fact.wide {
  grid-column: 1 / -1;
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
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tone-warning .reminder-fact {
  background: rgba(255, 255, 255, 0.72);
}
.tone-warning .reminder-service-action {
  color: var(--warning);
}
.reminder-service-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 9px;
  padding-top: 9px;
  border-top: 1px dashed rgba(28, 40, 37, 0.12);
}
.reminder-footer-note {
  min-width: 0;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reminder-service-link {
  min-height: 28px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 2px;
  color: var(--accent);
  font-size: 10px;
  font-weight: 650;
}
.archive-banner {
  min-height: 66px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 16px 0;
  padding: 11px 12px;
  border: 1px solid #ecd6c2;
  border-radius: 9px;
  background: #fff8f1;
}
.archive-banner.locked {
  border-color: #cfe6df;
  background: #f0faf6;
}
.archive-icon {
  width: 35px;
  height: 35px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: rgba(200, 100, 40, 0.1);
  color: var(--warning);
}
.archive-banner.locked .archive-icon {
  background: var(--accent-soft);
  color: var(--accent);
}
.archive-copy {
  flex: 1;
  min-width: 0;
}
.archive-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
}
.archive-note {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
}
.archive-action {
  flex: none;
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
}
.tab-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  margin: 18px 16px 0;
  padding: 4px;
  border-radius: 9px;
  background: #e8eeeb;
}
.tab-item {
  min-height: 39px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 7px;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 650;
}
.tab-item.active {
  background: var(--surface);
  color: var(--text-primary);
  box-shadow: 0 2px 8px rgba(20, 45, 38, 0.06);
}
.tab-count {
  min-width: 19px;
  height: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 8px;
}
.plan-section {
  margin: 22px 16px 0;
}
.section-head {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-kicker {
  display: block;
  margin-bottom: 3px;
}
.section-title {
  color: var(--ink);
  font-size: 18px;
  font-weight: 730;
  line-height: 24px;
}
.section-count {
  color: var(--text-muted);
  font-size: 10px;
}
.plan-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-top: 9px;
}
.plan-card {
  display: flex;
  align-items: stretch;
  gap: 11px;
  padding: 13px;
  border: 1px solid var(--border);
  border-left-width: 3px;
  border-radius: 10px;
  background: var(--surface);
}
.plan-card.status-1 {
  border-left-color: var(--accent);
}
.plan-card.status-0 {
  border-left-color: #b8c5c0;
}
.plan-card.status-3 {
  border-left-color: var(--warning);
}
.plan-rail {
  width: 47px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.plan-time {
  color: var(--ink);
  font-size: 13px;
  font-weight: 740;
  line-height: 18px;
}
.rail-line {
  width: 1px;
  flex: 1;
  min-height: 22px;
  margin: 6px 0;
  background: var(--border);
}
.plan-status {
  color: var(--accent);
  font-size: 8px;
  font-weight: 700;
  white-space: nowrap;
}
.status-0 .plan-status {
  color: var(--text-muted);
}
.status-3 .plan-status {
  color: var(--warning);
}
.plan-main {
  flex: 1;
  min-width: 0;
}
.plan-title-line {
  display: flex;
  align-items: flex-start;
  gap: 5px;
}
.plan-content {
  flex: 1;
  min-width: 0;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 660;
  line-height: 21px;
  word-break: break-all;
}
.plan-arrow {
  flex: none;
  margin-top: 2px;
  color: var(--text-muted);
}
.plan-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 8px;
}
.reminder-line {
  width: fit-content;
  max-width: 100%;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 7px;
  padding: 3px 7px;
  border-radius: 5px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-size: 11px;
  font-weight: 600;
  line-height: 17px;
}
.reminder-line.tone-warning {
  background: var(--warning-bg);
  color: #8b5128;
}
.reminder-line.tone-muted {
  background: var(--soft);
  color: var(--text-muted);
}
.meta-project {
  padding-left: 7px;
  border-left: 1px solid var(--border);
}
.progress-note {
  display: block;
  margin-top: 8px;
  padding: 7px 8px;
  overflow: hidden;
  border-radius: 6px;
  background: #f5f8f6;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-grid {
  display: flex;
  gap: 4px;
  margin-top: 10px;
}
.status-pill {
  min-width: 43px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 650;
}
.status-pill.selected {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-deep);
}
.plan-actions {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px solid var(--border);
}
.text-action {
  min-height: 25px;
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--accent);
  font-size: 9px;
  font-weight: 650;
}
.text-action.subtle {
  margin-left: auto;
  color: var(--text-muted);
}
.completed-section {
  margin-top: 24px;
  padding-bottom: 8px;
}
.completed-list,
.record-list {
  margin-top: 9px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.completed-row {
  min-height: 61px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}
.completed-row:last-child,
.record-card:last-child {
  border-bottom: 0;
}
.done-mark {
  width: 28px;
  height: 28px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.done-main {
  flex: 1;
  min-width: 0;
}
.done-title {
  display: block;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.done-meta {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 8px;
}
.done-arrow,
.record-arrow {
  flex: none;
  color: var(--text-muted);
}
.records-heading {
  margin: 22px 16px 0;
}
.record-entry {
  min-height: 30px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 0 9px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--accent);
  font-size: 9px;
  font-weight: 650;
}
.record-list {
  margin: 9px 16px 0;
}
.record-card {
  min-height: 90px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid var(--border);
}
.record-date-box {
  width: 43px;
  height: 49px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: var(--surface-soft);
}
.record-day {
  color: var(--ink);
  font-size: 18px;
  font-weight: 750;
  line-height: 21px;
}
.record-month {
  color: var(--text-muted);
  font-size: 8px;
}
.record-main {
  flex: 1;
  min-width: 0;
}
.record-head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.record-type {
  color: var(--accent);
  font-size: 8px;
  font-weight: 700;
}
.shared-tag {
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--work-soft);
  color: var(--work);
  font-size: 7px;
}
.record-content {
  display: -webkit-box;
  margin-top: 5px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  word-break: break-all;
}
.record-project {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.empty-panel {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 16px;
  padding: 26px;
  border: 1px dashed #cfdcd7;
  border-radius: 10px;
  text-align: center;
}
.empty-mark {
  width: 54px;
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: var(--surface);
  color: var(--accent);
  box-shadow: var(--shadow-soft);
}
.empty-title {
  margin-top: 16px;
  color: var(--ink);
  font-size: 16px;
  font-weight: 700;
}
.empty-desc {
  max-width: 260px;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 17px;
}
.empty-action {
  min-height: 36px;
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 16px;
  padding: 0 14px;
  border-radius: 6px;
  background: var(--accent);
  color: #ffffff;
  font-size: 10px;
  font-weight: 650;
}
.loading-state {
  min-height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 10px;
}
.scroll-space {
  height: calc(92px + env(safe-area-inset-bottom));
}
.sheet-mask {
  position: fixed;
  z-index: 300;
  inset: 0;
  display: flex;
  align-items: flex-end;
  background: rgba(14, 25, 21, 0.4);
}
.bottom-sheet {
  width: 100%;
  max-height: 88vh;
  overflow-y: auto;
  padding: 8px 16px 16px;
  border-radius: 14px 14px 0 0;
  background: var(--surface);
}
.sheet-handle {
  width: 36px;
  height: 4px;
  margin: 0 auto 13px;
  border-radius: 2px;
  background: #d8e1dd;
}
.sheet-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.sheet-kicker {
  display: block;
}
.sheet-title {
  display: block;
  margin-top: 4px;
  color: var(--ink);
  font-size: 21px;
  font-weight: 730;
  line-height: 27px;
}
.sheet-close {
  width: 34px;
  height: 34px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--soft);
  color: var(--text-secondary);
}
.sheet-plan {
  margin-top: 15px;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f7f9f8;
}
.sheet-plan-time {
  display: block;
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
}
.sheet-plan-content {
  display: block;
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 12px;
  line-height: 18px;
}
.sheet-textarea {
  width: 100%;
  min-height: 104px;
  margin-top: 12px;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f8faf9;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 21px;
}
.compact-textarea {
  min-height: 80px;
}
.voice-live {
  display: block;
  margin-top: 6px;
  padding: 0 3px;
  color: var(--accent);
  font-size: 9px;
  line-height: 15px;
}
.voice-input-row {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 11px;
}
.voice-input-button {
  min-height: 36px;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0 11px;
  border: 1px solid #cfe5df;
  border-radius: 7px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 10px;
  font-weight: 650;
}
.voice-input-button.recording {
  border-color: var(--warning);
  background: var(--warning-bg);
  color: var(--warning);
  animation: soft-pulse 1.8s infinite;
}
.voice-input-button.stopping {
  animation: none;
  opacity: 0.72;
}
.voice-tip {
  color: var(--text-muted);
  font-size: 8px;
}
.sheet-primary,
.sheet-secondary {
  height: 47px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 650;
  line-height: 47px;
}
.sheet-primary {
  width: 100%;
  margin-top: 16px;
  background: var(--accent);
  color: #ffffff;
}
.sheet-primary[disabled] {
  opacity: 0.6;
}
.postpone-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 14px;
}
.picker-card {
  min-height: 59px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 9px 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f8faf9;
}
.picker-label {
  color: var(--text-muted);
  font-size: 8px;
}
.picker-value {
  margin-top: 5px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}
.sheet-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
.sheet-secondary {
  width: 95px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
}
.flex-primary {
  flex: 1;
  margin-top: 0;
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Final mobile readability pass. */
.header-action,
.archive-action,
.tab-item,
.text-action {
  letter-spacing: 0;
}
.plan-hero,
.archive-banner,
.plan-card,
.completed-list,
.record-list {
  border-radius: 8px;
}
.hero-kicker,
.section-kicker,
.sheet-kicker {
  font-size: 10px;
  letter-spacing: 0;
}
.hero-date,
.stat-label,
.section-count {
  font-size: 11px;
}
.voice-note,
.archive-note {
  font-size: 11px;
  line-height: 17px;
}
.archive-title,
.record-content {
  font-size: 13px;
}
.tab-count {
  font-size: 10px;
}
.plan-status,
.plan-meta,
.progress-note,
.done-meta,
.record-type,
.record-project {
  font-size: 11px;
}
.progress-note {
  line-height: 17px;
  white-space: normal;
}
.status-pill {
  height: 30px;
  font-size: 11px;
}
.text-action {
  min-height: 32px;
  font-size: 11px;
}
.done-title,
.record-content {
  line-height: 20px;
}
.record-entry,
.voice-input-button,
.sheet-primary,
.sheet-secondary {
  font-size: 13px;
}
@media (max-width: 360px) {
  .reminder-service-action {
    padding: 0 7px;
    font-size: 10px;
  }
  .status-grid {
    flex-wrap: wrap;
  }
}
</style>
