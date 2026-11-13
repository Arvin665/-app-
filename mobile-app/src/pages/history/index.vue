<template>
  <view class="history-page app-page">
    <PageHeader title="历史归档" fallback="/pages/home/index">
      <template #actions>
        <view class="header-action pressable" @tap="openMaterialsLibrary">资料总库</view>
      </template>
    </PageHeader>

    <view class="history-top">
      <view class="tab-switch">
        <view class="tab-item pressable" :class="{ active: tab === 'records' }" @tap="switchTab('records')">
          <NotebookTabs :size="16" />
          <text>业务记录</text>
          <text v-if="tab === 'records'" class="tab-count">{{ recordTotal }}</text>
        </view>
        <view class="tab-item pressable" :class="{ active: tab === 'materials' }" @tap="switchTab('materials')">
          <Archive :size="16" />
          <text>资料原件</text>
          <text v-if="tab === 'materials'" class="tab-count">{{ materialTotal }}</text>
        </view>
      </view>

      <view class="search-shell">
        <Search :size="17" class="search-icon" />
        <input
          v-model="keyword"
          class="search-input"
          confirm-type="search"
          :placeholder="tab === 'records' ? '搜项目、企业、记录正文' : '搜文件名、资料正文'"
          @input="queueSearch"
          @confirm="refresh"
        />
        <view class="voice-search pressable" :class="{ listening }" @tap="toggleVoiceSearch">
          <Square v-if="listening" :size="13" fill="currentColor" />
          <Mic v-else :size="16" />
        </view>
      </view>
      <text v-if="listening || voiceInterim" class="listening-note">{{ voiceInterim || "正在听，说出要查找的内容..." }}</text>

      <scroll-view class="filter-scroll" scroll-x :show-scrollbar="false">
        <view class="filter-row">
          <view
            v-for="item in filters"
            :key="item.key"
            class="filter-chip pressable"
            :class="{ active: moduleFilter === item.key }"
            @tap="selectModule(item.key)"
          >
            {{ item.label }}
          </view>
          <view v-if="tab === 'materials'" class="filter-chip action-chip pressable" :class="{ active: fileType }" @tap="chooseFileType">
            <SlidersHorizontal :size="12" />
            <text>{{ fileType ? typeLabel(fileType) : "全部格式" }}</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <scroll-view class="history-scroll" scroll-y @scrolltolower="loadMore">
      <view class="result-line">
        <text>{{ loading ? "正在翻阅..." : `共 ${currentTotal} 条` }}</text>
        <text class="result-filter">{{ activeFilterLabel }}</text>
      </view>

      <template v-if="tab === 'records'">
        <view v-if="records.length" class="record-list">
          <view
            v-for="item in records"
            :key="`${item.module}-${item.record_id}`"
            class="record-card pressable"
            @tap="openRecord(item)"
          >
            <ModuleMark :module-key="item.module" size="sm" />
            <view class="record-main">
              <view class="record-head">
                <text class="module-label">{{ moduleNames[item.module] }}</text>
                <text class="record-date">{{ item.displayDate || "日期待补" }}</text>
              </view>
              <text class="record-title">{{ item.displayTitle }}</text>
              <text class="record-summary">{{ item.displaySummary || "还没有补充说明" }}</text>
            </view>
            <ChevronRight :size="15" class="row-arrow" />
          </view>
        </view>
      </template>

      <template v-else>
        <view v-if="materials.length" class="material-list">
          <MaterialRow
            v-for="item in materials"
            :key="item.material_id"
            :material="item"
            :show-module="moduleFilter === 'all'"
            @open="openMaterial"
          />
        </view>
      </template>

      <view v-if="!loading && !currentTotal" class="empty-history">
        <view class="empty-mark"><NotebookTabs :size="25" /></view>
        <text class="empty-title">没有找到对应内容</text>
        <text class="empty-desc">{{ keyword ? "换一种说法，或清除筛选后再看。" : tab === "records" ? "这个模块还没有记录。" : "这个模块还没有资料。" }}</text>
        <view class="empty-action pressable" @tap="clearFilters">清除筛选</view>
      </view>

      <view v-if="loading && !currentTotal" class="loading-state"><LoaderCircle :size="21" class="spin" /><text>正在读取</text></view>
      <view v-if="loadingMore" class="loading-more"><LoaderCircle :size="15" class="spin" /><text>继续加载</text></view>
      <view v-if="currentTotal && !hasMore && !loadingMore" class="all-loaded">已经翻到最早一条</view>
      <view class="scroll-space"></view>
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad, onPullDownRefresh } from "@dcloudio/uni-app";
import {
  Archive,
  ChevronRight,
  LoaderCircle,
  Mic,
  NotebookTabs,
  Search,
  SlidersHorizontal,
  Square,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import ModuleMark from "../../components/ModuleMark.vue";
import MaterialRow from "../../components/MaterialRow.vue";
import { moduleList, recordDate, recordTitle } from "../../data/modules";
import { request } from "../../services/api";
import { cacheRecords, getCachedRecords } from "../../services/localDb";
import { listMaterials, materialTypeLabels } from "../../services/material";
import { dictationAvailable, startDictation } from "../../services/voice";
import { ensureBound } from "../../services/session";

const tab = ref("records");
const keyword = ref("");
const moduleFilter = ref("all");
const fileType = ref("");
const records = ref([]);
const materials = ref([]);
const recordTotal = ref(0);
const materialTotal = ref(0);
const recordPage = ref(1);
const materialPage = ref(1);
const loading = ref(false);
const loadingMore = ref(false);
const listening = ref(false);
const voiceInterim = ref("");
const pageSize = 30;
let searchTimer = null;
let voiceSession = null;

const moduleNames = Object.fromEntries(moduleList.map((item) => [item.key, item.visual.short]));
const filters = computed(() => [
  { key: "all", label: "全部" },
  ...moduleList.map((item) => ({ key: item.key, label: item.visual.short })),
]);
const currentTotal = computed(() => (tab.value === "records" ? recordTotal.value : materialTotal.value));
const activeFilterLabel = computed(() => {
  const module = moduleFilter.value === "all" ? "全部模块" : moduleNames[moduleFilter.value];
  return tab.value === "materials" && fileType.value ? `${module} · ${typeLabel(fileType.value)}` : module;
});
const hasMore = computed(() => {
  if (tab.value === "records") return records.value.length < recordTotal.value;
  return materials.value.length < materialTotal.value;
});

function typeLabel(value) {
  return materialTypeLabels[value] || "其他格式";
}

function summaryFor(module, record) {
  if (module === "sale") {
    return [record.district, record.deal_total_price ? `${record.deal_total_price} 万元` : "", record.deal_status]
      .filter((value) => value && !String(value).startsWith("待"))
      .join(" · ");
  }
  if (module === "lease") {
    return [record.industry, record.new_project, record.area || record.new_area ? `${record.new_area || record.area} ㎡` : ""]
      .filter(Boolean)
      .join(" · ");
  }
  if (module === "work") return [record.related_project, record.follow_status, record.is_shared ? "团队共享" : "仅本人可见"].filter(Boolean).join(" · ");
  return [record.inspiration_type, record.tags].filter(Boolean).join(" · ");
}

function switchTab(next) {
  if (tab.value === next) return;
  tab.value = next;
  refresh();
}

function selectModule(key) {
  moduleFilter.value = key;
  refresh();
}

function chooseFileType() {
  uni.showActionSheet({
    itemList: ["全部格式", "图片", "PDF", "表格", "文档", "演示", "文本", "音视频", "其他"],
    success: (result) => {
      const values = ["", "image", "pdf", "excel", "word", "presentation", "text", "video", "other"];
      fileType.value = values[result.tapIndex] || "";
      refresh();
    },
  });
}

function clearFilters() {
  keyword.value = "";
  moduleFilter.value = "all";
  fileType.value = "";
  refresh();
}

function refresh() {
  if (tab.value === "records") loadRecords(true);
  else loadMaterials(true);
}

async function loadRecords(reset = false) {
  if (loading.value || loadingMore.value) return;
  if (reset) {
    loading.value = true;
    recordPage.value = 1;
    records.value = [];
  } else {
    loadingMore.value = true;
  }
  const configs = moduleFilter.value === "all" ? moduleList : [moduleList.find((item) => item.key === moduleFilter.value)];
  const results = await Promise.allSettled(
    configs.map(async (module) => {
      try {
        const response = await request(
          `/${module.endpoint}?page=${recordPage.value}&page_size=${pageSize}&keyword=${encodeURIComponent(keyword.value.trim())}`,
        );
        if (recordPage.value === 1) await cacheRecords(module.key, response.items || [], new Date().toISOString());
        return { module: module.key, response, cached: false };
      } catch (error) {
        const cached = await getCachedRecords(module.key);
        const query = keyword.value.trim();
        const filtered = cached.filter((record) => !query || JSON.stringify(record).includes(query));
        return {
          module: module.key,
          response: { items: filtered.slice(0, pageSize), total: filtered.length },
          cached: true,
        };
      }
    }),
  );

  const fresh = results.flatMap((result) => {
    if (result.status !== "fulfilled") return [];
    const { module, response } = result.value;
    return (response.items || []).map((record) => ({
      ...record,
      module,
      displayDate: recordDate(module, record),
      displayTitle: recordTitle(module, record),
      displaySummary: summaryFor(module, record),
    }));
  });
  recordTotal.value = results.reduce((sum, result) => sum + (result.status === "fulfilled" ? Number(result.value.response.total || 0) : 0), 0);
  const merged = reset ? fresh : [...records.value, ...fresh];
  records.value = Array.from(new Map(merged.map((item) => [`${item.module}-${item.record_id}`, item])).values()).sort(
    (a, b) => (b.displayDate || "").localeCompare(a.displayDate || ""),
  );
  loading.value = false;
  loadingMore.value = false;
}

async function loadMaterials(reset = false) {
  if (loading.value || loadingMore.value) return;
  if (reset) {
    loading.value = true;
    materialPage.value = 1;
    materials.value = [];
  } else {
    loadingMore.value = true;
  }
  try {
    const response = await listMaterials({
      module: moduleFilter.value === "all" ? undefined : moduleFilter.value,
      fileType: fileType.value || undefined,
      keyword: keyword.value.trim() || undefined,
      page: materialPage.value,
      pageSize,
    });
    const incoming = response.items || [];
    materials.value = reset ? incoming : [...materials.value, ...incoming];
    materialTotal.value = Number(response.total || 0);
  } catch (error) {
    uni.showToast({ title: error.message || "资料加载失败", icon: "none" });
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function loadMore() {
  if (!hasMore.value || loading.value || loadingMore.value) return;
  if (tab.value === "records") {
    recordPage.value += 1;
    loadRecords(false);
  } else {
    materialPage.value += 1;
    loadMaterials(false);
  }
}

function queueSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => refresh(), 360);
}

function openRecord(item) {
  uni.navigateTo({ url: `/pages/detail/index?module=${item.module}&id=${item.record_id}` });
}

function openMaterial(item) {
  uni.navigateTo({ url: `/pages/material/index?id=${item.material_id}` });
}

function openMaterialsLibrary() {
  uni.navigateTo({ url: "/pages/materials/index" });
}

function toggleVoiceSearch() {
  if (listening.value) {
    voiceSession?.stop?.();
    return;
  }
  if (!dictationAvailable()) {
    uni.showModal({
      title: "当前环境没有语音识别",
      content: "可以使用 Edge/Chrome 或 App 原生语音模块，也可以直接输入关键词。",
      showCancel: false,
    });
    return;
  }
  listening.value = true;
  voiceInterim.value = "";
  voiceSession = startDictation({
    continuous: false,
    onInterim: (text) => {
      voiceInterim.value = text;
    },
    onFinal: (text) => {
      if (!text.trim()) return;
      keyword.value = text.trim();
      refresh();
    },
    onError: (error) => uni.showToast({ title: error.message || "语音搜索暂不可用", icon: "none" }),
    onEnd: () => {
      listening.value = false;
      voiceSession = null;
    },
  });
  if (!voiceSession) listening.value = false;
}

onLoad((options) => {
  if (!ensureBound()) return;
  if (moduleList.some((item) => item.key === options?.module)) moduleFilter.value = options.module;
  loadRecords(true);
});

onPullDownRefresh(async () => {
  loading.value = false;
  loadingMore.value = false;
  await (tab.value === "records" ? loadRecords(true) : loadMaterials(true));
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
.history-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.header-action {
  min-height: 32px;
  display: flex;
  align-items: center;
  padding: 0 7px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 650;
}
.history-top {
  flex: none;
  padding: 3px 16px 0;
}
.tab-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border-radius: 9px;
  background: #e9efec;
}
.tab-item {
  min-height: 38px;
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
  min-width: 20px;
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
.search-shell {
  height: 44px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 0 6px 0 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.search-icon {
  flex: none;
  color: var(--text-muted);
}
.search-input {
  flex: 1;
  min-width: 0;
  height: 42px;
  font-size: 12px;
}
.voice-search {
  width: 33px;
  height: 33px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.voice-search.listening {
  background: var(--warning-bg);
  color: var(--warning);
  animation: soft-pulse 1.8s infinite;
}
.listening-note {
  display: block;
  margin-top: 5px;
  padding: 0 4px;
  color: var(--accent);
  font-size: 9px;
}
.filter-scroll {
  width: 100%;
  margin-top: 9px;
  white-space: nowrap;
}
.filter-row {
  display: inline-flex;
  gap: 6px;
  padding-right: 12px;
}
.filter-chip {
  height: 29px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 9px;
  font-weight: 600;
}
.filter-chip.active {
  border-color: var(--ink);
  background: var(--ink);
  color: #ffffff;
}
.action-chip {
  color: var(--accent);
}
.action-chip.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-deep);
}
.history-scroll {
  flex: 1;
  min-height: 0;
  padding: 0 16px;
}
.result-line {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 9px;
}
.result-filter {
  color: var(--text-secondary);
}
.record-list,
.material-list {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.record-card {
  min-height: 90px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid var(--border);
}
.record-card:last-child {
  border-bottom: 0;
}
.record-main {
  flex: 1;
  min-width: 0;
}
.record-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.module-label {
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 700;
}
.record-date {
  flex: none;
  color: var(--text-muted);
  font-size: 8px;
}
.record-title {
  display: block;
  margin-top: 5px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
  line-height: 19px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.record-summary {
  display: -webkit-box;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 10px;
  line-height: 16px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.row-arrow {
  flex: none;
  margin-top: 26px;
  color: var(--text-muted);
}
.material-list {
  padding: 0 12px;
}
.empty-history,
.loading-state {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 22px;
  text-align: center;
}
.empty-mark {
  width: 58px;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 17px;
  background: var(--surface);
  color: var(--accent);
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
  min-height: 34px;
  display: flex;
  align-items: center;
  margin-top: 15px;
  padding: 0 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--accent);
  font-size: 10px;
  font-weight: 650;
}
.loading-state {
  min-height: 180px;
  flex-direction: row;
  gap: 8px;
  color: var(--text-muted);
  font-size: 10px;
}
.loading-more,
.all-loaded {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 15px;
  color: var(--text-muted);
  font-size: 9px;
}
.scroll-space {
  height: calc(22px + env(safe-area-inset-bottom));
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
