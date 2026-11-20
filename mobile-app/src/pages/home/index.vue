<template>
  <view class="home-page app-page safe-top tabbar-space">
    <view class="home-top">
      <view>
        <view class="brand-line"><view class="brand-dot"></view><text class="brand-name">Sayo</text><text class="brand-suffix">Sense</text></view>
        <text class="home-greeting">把知道的事，留给下一次判断。</text>
      </view>
      <view class="sync-status" :class="{ pending: pendingCount > 0, error: dashboardError, loading: loadingDashboard }">
        <LoaderCircle v-if="loadingDashboard" :size="14" class="spin" />
        <CloudOff v-else-if="dashboardError" :size="14" />
        <CloudOff v-else-if="pendingCount" :size="14" />
        <CloudCheck v-else :size="14" />
        <text>{{ loadingDashboard ? "同步中" : dashboardError ? "同步异常" : pendingCount ? `${pendingCount} 条待同步` : "已同步" }}</text>
      </view>
    </view>

    <StatusNotice
      v-if="dashboardError"
      tone="warning"
      title="首页数据没有完全同步"
      :message="dashboardError"
      action-text="重新同步"
      @action="loadDashboard"
    />

    <view class="today-strip">
      <view><text class="today-number">{{ todayRecords }}</text><text class="today-label">今日记录</text></view>
      <view><text class="today-number">{{ materialTotal }}</text><text class="today-label">份资料</text></view>
      <view class="today-date"><text>{{ todayDisplay }}</text><text>{{ weekday }}</text></view>
    </view>

    <view v-if="todayPlansLoaded" class="today-tasks-entry pressable" @tap="openTodayTasks">
      <view class="today-task-icon"><CalendarCheck2 :size="17" /></view>
      <view class="today-task-copy">
        <view class="today-task-title-row">
          <text class="today-task-title">今日待办</text>
          <text v-if="todayPlans.length" class="today-task-count">{{ todayCompleted }}/{{ todayPlans.length }}</text>
        </view>
        <text class="today-task-desc">{{ todayTaskSummary }}</text>
      </view>
      <ChevronRight :size="16" class="today-task-arrow" />
    </view>

    <view v-if="showDailyBanner" class="daily-banner pressable" @tap="openDailyPlans">
      <view class="banner-icon"><CalendarCheck2 :size="18" /></view>
      <view class="banner-copy"><text class="banner-title">今天的计划还没有确认</text><text class="banner-note">花一分钟收好今天的工作节奏</text></view>
      <ChevronRight :size="18" />
    </view>

    <view class="voice-launch pressable" @tap="openVoiceLauncher">
      <view class="voice-launch-copy">
        <text class="voice-kicker">NEW ASSET</text>
        <text class="voice-title">想到什么，直接说</text>
        <text class="voice-desc">项目、客户、工作或灵感，说给我听。</text>
      </view>
      <view class="voice-orb"><Mic :size="25" :stroke-width="1.9" /></view>
    </view>

    <view class="section-heading home-section-heading">
      <view><text class="section-kicker">YOUR WORKSPACE</text><text class="section-title">四个资料入口</text></view>
      <text class="section-link" @tap="openHistory">全部记录</text>
    </view>

    <view class="module-grid">
      <view
        v-for="item in homeModules"
        :key="item.key"
        class="module-card pressable"
        :class="[`tone-${item.key}`]"
        @tap="openModule(item.key)"
      >
        <view class="module-top">
          <ModuleMark :module-key="item.key" size="md" />
          <ArrowUpRight :size="17" class="module-arrow" />
        </view>
        <text class="module-name">{{ item.visual.short }}</text>
        <text class="module-desc">{{ item.visual.description }}</text>
        <view class="module-footer">
          <text class="module-count">{{ counts[item.key] ?? "—" }} 条</text>
          <text class="module-update">{{ latest[item.key] || "还没有记录" }}</text>
        </view>
      </view>
    </view>

    <view class="archive-strip pressable" @tap="openMaterials">
      <view class="archive-icon"><Archive :size="20" /></view>
      <view class="archive-copy">
        <text class="archive-title">资料总库</text>
        <text class="archive-desc">图片、文件、表格，任何格式都能留下。</text>
      </view>
      <text class="archive-total">{{ materialTotal }} <text class="archive-unit">份</text></text>
      <ChevronRight :size="17" />
    </view>

    <view v-if="recent.length" class="recent-block">
      <view class="section-heading"><text class="section-title small">最近留下</text><text class="section-link" @tap="openHistory">翻看</text></view>
      <view v-for="item in recent" :key="item.key" class="recent-row pressable" @tap="openRecord(item)">
        <ModuleMark :module-key="item.module" size="sm" />
        <view class="recent-copy"><text class="recent-title">{{ item.title }}</text><text class="recent-meta">{{ item.moduleName }} · {{ item.date || "刚刚" }}</text></view>
        <ChevronRight :size="16" class="recent-arrow" />
      </view>
    </view>

    <AppTabBar active="home" />
    <TodayTasksModal
      :visible="todayTasksVisible"
      :plans="todayPlans"
      :date="today"
      :locked="todayPlansLocked"
      :updating-id="updatingPlanId"
      :loading="todayPlansLoading"
      :error="todayPlansError"
      @close="todayTasksVisible = false"
      @update-status="updateTodayTaskStatus"
      @open-plans="openPlansFromToday"
      @retry="loadDashboard"
    />
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onPullDownRefresh, onShow } from "@dcloudio/uni-app";
import { Archive, ArrowUpRight, CalendarCheck2, ChevronRight, CloudCheck, CloudOff, LoaderCircle, Mic } from "@lucide/vue";
import AppTabBar from "../../components/AppTabBar.vue";
import ModuleMark from "../../components/ModuleMark.vue";
import StatusNotice from "../../components/StatusNotice.vue";
import TodayTasksModal from "../../components/TodayTasksModal.vue";
import { homeModules, localDate, moduleList, recordDate, recordTitle } from "../../data/modules";
import { ensureBound } from "../../services/session";
import { request } from "../../services/api";
import { listOfflineQueue } from "../../services/localDb";

const showDailyBanner = ref(false);
const dashboardError = ref("");
const loadingDashboard = ref(false);
const counts = ref({});
const latest = ref({});
const recent = ref([]);
const todayRecords = ref(0);
const materialTotal = ref(0);
const pendingCount = ref(0);
const todayPlans = ref([]);
const todayPlansLocked = ref(false);
const todayPlansError = ref("");
const todayPlansLoading = ref(false);
const todayPlansLoaded = ref(false);
const todayTasksVisible = ref(false);
const updatingPlanId = ref("");
const today = localDate();
const now = new Date();
const todayDisplay = `${String(now.getMonth() + 1).padStart(2, "0")}/${String(now.getDate()).padStart(2, "0")}`;
const weekday = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][now.getDay()];
let autoOpenHandled = false;
const todayCompleted = computed(() => todayPlans.value.filter((plan) => Number(plan.ext_field_5 ?? 0) === 2).length);
const todayPending = computed(() => todayPlans.value.filter((plan) => Number(plan.ext_field_5 ?? 0) !== 2).length);
const todayTaskSummary = computed(() => {
  if (todayPlansLoading.value && !todayPlansLoaded.value) return "正在同步今天的计划";
  if (todayPlansError.value) return "今日待办同步失败，点开查看";
  if (!todayPlans.value.length) return "今天还没有计划，点开添加";
  return todayPending.value ? `${todayPending.value} 项还没完成，点开更新进度` : "今天的事项都完成了";
});

function openModule(module) {
  if (!ensureBound()) return;
  uni.navigateTo({ url: `/pages/module/index?module=${module}` });
}

function openVoiceLauncher() {
  uni.showActionSheet({
    itemList: ["说一条项目买卖资讯", "说一条企业租赁信息", "记一条工作安排", "记一个个人灵感"],
    success: (result) => {
      const key = ["sale", "lease", "work", "inspiration"][result.tapIndex];
      uni.navigateTo({ url: `/pages/entry/index?module=${key}&voice=1` });
    },
  });
}

function openHistory() {
  uni.navigateTo({ url: "/pages/history/index" });
}

function openMaterials() {
  uni.navigateTo({ url: "/pages/materials/index" });
}

function openRecord(item) {
  uni.navigateTo({ url: `/pages/detail/index?module=${item.module}&id=${item.recordId}` });
}

function openDailyPlans() {
  uni.navigateTo({ url: "/pages/plans/index" });
}

function openTodayTasks() {
  todayTasksVisible.value = true;
}

function openPlansFromToday() {
  todayTasksVisible.value = false;
  setTimeout(openDailyPlans, 220);
}

function replaceTodayPlan(updated) {
  todayPlans.value = todayPlans.value.map((item) => (
    item.record_id === updated.record_id ? { ...item, ...updated } : item
  ));
}

async function updateTodayTaskStatus({ plan, status }) {
  if (todayPlansLocked.value || updatingPlanId.value === plan.record_id) return;
  const previousStatus = plan.ext_field_5;
  updatingPlanId.value = plan.record_id;
  replaceTodayPlan({ ...plan, ext_field_5: status });
  try {
    const updated = await request(`/work-logs/${plan.record_id}/status`, {
      method: "POST",
      data: { status, note: "" },
    });
    replaceTodayPlan(updated);
    uni.showToast({ title: "进度已更新", icon: "success", duration: 1200 });
  } catch (error) {
    replaceTodayPlan({ ...plan, ext_field_5: previousStatus });
    uni.showToast({
      title: error.message || "进度更新失败，请稍后重试",
      icon: "none",
      duration: 3000,
    });
  } finally {
    if (updatingPlanId.value === plan.record_id) updatingPlanId.value = "";
  }
}

function openTodayTasksOnLaunch() {
  if (autoOpenHandled) return;
  autoOpenHandled = true;
  todayTasksVisible.value = true;
}

async function loadDashboard() {
  if (!ensureBound() || loadingDashboard.value) return;
  loadingDashboard.value = true;
  dashboardError.value = "";

  const auxiliaryResultsPromise = Promise.allSettled([
    listOfflineQueue(),
    request("/materials?page_size=1"),
  ]);
  const dashboardFailures = [];
  todayPlansLoading.value = true;
  todayPlansError.value = "";
  openTodayTasksOnLaunch();
  try {
    const todayPlansResult = await request(`/work-logs/plans?record_date=${today}`);
    todayPlans.value = todayPlansResult.items || [];
    todayPlansLocked.value = Boolean(todayPlansResult.locked);
  } catch (error) {
    todayPlansError.value = error.message || "今日待办没有同步";
    dashboardFailures.push(todayPlansError.value);
  } finally {
    todayPlansLoaded.value = true;
    todayPlansLoading.value = false;
  }

  const [queueResult, materialResult] = await auxiliaryResultsPromise;
  if (queueResult.status === "fulfilled") pendingCount.value = queueResult.value.length;
  else dashboardFailures.push("本机待同步队列暂时无法读取");
  if (materialResult.status === "fulfilled") materialTotal.value = Number(materialResult.value.total || 0);
  else dashboardFailures.push(materialResult.reason?.message || "资料总数没有同步");
  const results = await Promise.allSettled(
    moduleList.map(async (module) => {
      const [response, todayResponse] = await Promise.all([
        request(`/${module.endpoint}?page_size=8`),
        request(`/${module.endpoint}?page_size=1&start_date=${today}&end_date=${today}`),
      ]);
      const items = response.items || [];
      counts.value[module.key] = Number(response.total || items.length);
      latest.value[module.key] = items[0] ? recordDate(module.key, items[0]) : "";
      return {
        todayCount: Number(todayResponse.total || 0),
        items: items.map((record) => ({
          key: `${module.key}-${record.record_id}`,
          module: module.key,
          moduleName: module.visual.short,
          recordId: record.record_id,
          title: recordTitle(module.key, record),
          date: recordDate(module.key, record),
        })),
      };
    }),
  );
  const failedModules = results.filter((result) => result.status === "rejected");
  if (failedModules.length) {
    const message = failedModules[0].reason?.message || "部分业务模块暂时没有连上";
    dashboardFailures.push(`${failedModules.length} 个模块没有同步：${message}`);
  }
  const all = results.flatMap((result) => (result.status === "fulfilled" ? result.value.items : []));
  recent.value = all.filter((item) => item.date).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4);
  todayRecords.value = results.reduce(
    (sum, result) => sum + (result.status === "fulfilled" ? result.value.todayCount : 0),
    0,
  );
  if (dashboardFailures.length) {
    dashboardError.value = Array.from(new Set(dashboardFailures)).join("；");
  }
  await checkDailyBanner();
  loadingDashboard.value = false;
}

async function checkDailyBanner() {
  const current = new Date();
  if (current.getHours() < 17 || (current.getHours() === 17 && current.getMinutes() < 30)) {
    showDailyBanner.value = false;
    return;
  }
  showDailyBanner.value = Boolean(todayPlans.value.length && !todayPlansLocked.value);
}

onShow(loadDashboard);

onPullDownRefresh(async () => {
  await loadDashboard();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
.home-page { padding: calc(16px + env(safe-area-inset-top)) 16px 0; overflow: hidden; }
.home-page :deep(.status-notice) {
  margin-left: 0;
  margin-right: 0;
}
.home-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.brand-line { display: flex; align-items: center; gap: 6px; }
.brand-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
.brand-name, .section-kicker { color: var(--text-muted); font-size: 10px; font-weight: 750; letter-spacing: 0.12em; }
.brand-line .brand-name { color: var(--ink); font-size: 11px; letter-spacing: 0; }
.brand-suffix { color: var(--text-muted); font-size: 8px; font-weight: 650; letter-spacing: 0; }
.home-greeting { display: block; max-width: 290px; margin-top: 8px; color: var(--ink); font-size: 23px; font-weight: 760; line-height: 31px; }
.sync-status { min-height: 30px; display: flex; align-items: center; gap: 5px; padding: 0 9px; border: 1px solid var(--border); border-radius: 999px; background: var(--surface); color: var(--text-secondary); font-size: 10px; white-space: nowrap; }
.sync-status.pending { border-color: #f0d7c0; background: var(--warning-bg); color: var(--warning); }
.sync-status.error { border-color: #ead4cf; background: #fff7f5; color: var(--danger); }
.sync-status.loading { border-color: #cfe5df; background: var(--accent-soft); color: var(--accent); }
.today-strip { display: grid; grid-template-columns: 1fr 1fr 1.2fr; margin-top: 20px; padding: 13px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.today-strip > view { min-width: 0; padding: 0 12px; border-right: 1px solid var(--border); }
.today-strip > view:first-child { padding-left: 0; }
.today-strip > view:last-child { padding-right: 0; border-right: 0; text-align: right; }
.today-number { display: block; color: var(--ink); font-size: 23px; font-weight: 760; line-height: 28px; }
.today-label, .today-date text { display: block; margin-top: 2px; color: var(--text-muted); font-size: 10px; line-height: 15px; }
.today-date text:first-child { margin-top: 3px; color: var(--text-secondary); font-size: 16px; font-weight: 700; }
.today-tasks-entry { min-height: 56px; display: flex; align-items: center; gap: 9px; margin-top: 12px; padding: 9px 11px; border: 1px solid #cfe5df; border-radius: var(--radius); background: #f7fcfa; }
.today-task-icon { width: 32px; height: 32px; flex: none; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: var(--accent-soft); color: var(--accent); }
.today-task-copy { flex: 1; min-width: 0; }
.today-task-title-row { display: flex; align-items: center; gap: 7px; }
.today-task-title { color: var(--text-primary); font-size: 12px; font-weight: 700; }
.today-task-count { color: var(--accent); font-size: 10px; font-weight: 700; }
.today-task-desc { display: block; margin-top: 2px; color: var(--text-muted); font-size: 9px; line-height: 14px; }
.today-task-arrow { flex: none; color: var(--accent); }
.daily-banner { min-height: 58px; display: flex; align-items: center; gap: 10px; margin-top: 14px; padding: 10px 12px; border: 1px solid #ecd8c6; border-radius: var(--radius); background: var(--warning-bg); color: var(--warning); }
.banner-icon { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: rgba(255, 255, 255, 0.55); }
.banner-copy { flex: 1; }
.banner-title { display: block; font-size: 12px; font-weight: 700; }
.banner-note { display: block; margin-top: 3px; color: #a9724d; font-size: 10px; }
.voice-launch { min-height: 136px; display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-top: 18px; padding: 20px; overflow: hidden; border-radius: 12px; background: var(--ink); color: #ffffff; box-shadow: 0 12px 28px rgba(22, 34, 31, 0.17); }
.voice-launch-copy { min-width: 0; display: flex; flex-direction: column; }
.voice-kicker { color: #8ed8c8; font-size: 10px; font-weight: 750; letter-spacing: 0.12em; }
.voice-title { display: block; margin-top: 12px; font-size: 22px; font-weight: 740; line-height: 29px; }
.voice-desc { display: block; margin-top: 6px; color: #bfd0ca; font-size: 11px; line-height: 17px; }
.voice-orb { width: 64px; height: 64px; flex: none; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(162, 238, 217, 0.48); border-radius: 50%; background: #1d4d43; color: #c4f8ea; animation: soft-pulse 2.8s infinite; }
.home-section-heading { margin-top: 24px; }
.section-kicker { display: block; margin-bottom: 4px; }
.module-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
.module-card { min-height: 164px; display: flex; flex-direction: column; padding: 14px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); }
.module-card.tone-sale { border-color: #f0d5cb; background: #fffaf8; }
.module-card.tone-lease { border-color: #cce8e2; background: #f8fffd; }
.module-card.tone-work { border-color: #d3ddec; background: #f9fbff; }
.module-card.tone-inspiration { border-color: #ead5dc; background: #fffafb; }
.module-top { display: flex; align-items: flex-start; justify-content: space-between; }
.module-arrow { color: var(--text-muted); }
.module-name { display: block; margin-top: 14px; color: var(--ink); font-size: 20px; font-weight: 740; line-height: 25px; }
.module-desc { display: block; margin-top: 4px; color: var(--text-secondary); font-size: 10px; line-height: 15px; }
.module-footer { display: flex; align-items: flex-end; justify-content: space-between; gap: 6px; margin-top: auto; padding-top: 12px; }
.module-count { color: var(--text-primary); font-size: 11px; font-weight: 700; white-space: nowrap; }
.module-update { overflow: hidden; color: var(--text-muted); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.archive-strip { min-height: 70px; display: flex; align-items: center; gap: 10px; margin-top: 12px; padding: 12px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); }
.archive-icon { width: 38px; height: 38px; flex: none; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: var(--surface-soft); color: var(--accent); }
.archive-copy { flex: 1; min-width: 0; }
.archive-title { display: block; color: var(--text-primary); font-size: 13px; font-weight: 700; }
.archive-desc { display: block; margin-top: 3px; color: var(--text-muted); font-size: 10px; }
.archive-total { color: var(--accent); font-size: 20px; font-weight: 740; }
.archive-unit { color: var(--text-muted); font-size: 10px; font-weight: 500; }
.recent-block { margin-top: 24px; padding-bottom: 12px; }
.section-title.small { font-size: 17px; }
.recent-row { min-height: 62px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--border); }
.recent-copy { flex: 1; min-width: 0; }
.recent-title { display: block; overflow: hidden; color: var(--text-primary); font-size: 13px; font-weight: 620; text-overflow: ellipsis; white-space: nowrap; }
.recent-meta { display: block; margin-top: 3px; color: var(--text-muted); font-size: 10px; }
.recent-arrow { color: var(--text-muted); }
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
