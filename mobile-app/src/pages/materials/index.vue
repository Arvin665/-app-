<template>
  <view class="materials-page app-page tabbar-space">
    <view class="materials-top safe-top">
      <view class="top-copy">
        <view class="brand-line"><view class="brand-dot"></view><text class="brand-name">MATERIAL ARCHIVE</text></view>
        <text class="page-title">所有资料</text>
        <text class="page-subtitle">{{ total }} 份原件与正文，随时回来翻看。</text>
      </view>
      <view class="upload-button pressable" @tap="startUpload">
        <LoaderCircle v-if="uploading" :size="20" class="spin" />
        <Plus v-else :size="21" />
      </view>
    </view>

    <view class="search-shell">
      <Search :size="18" class="search-icon" />
      <input
        v-model="keyword"
        class="search-input"
        confirm-type="search"
        placeholder="搜项目、文件、正文内容"
        @input="queueSearch"
        @confirm="loadMaterials(true)"
      />
      <view class="search-mic pressable" :class="{ listening, stopping: voicePhase === 'stopping' }" @tap="toggleVoiceSearch">
        <Square v-if="listening" :size="14" fill="currentColor" />
        <Mic v-else :size="17" />
      </view>
    </view>
    <text v-if="listening || voiceInterim" class="voice-search-line">{{ voiceInterim || (voicePhase === "stopping" ? "正在收尾，请稍等..." : "正在听，再按一下结束并搜索...") }}</text>

    <scroll-view class="filter-scroll" scroll-x :show-scrollbar="false">
      <view class="filter-row">
        <view
          v-for="item in moduleFilters"
          :key="item.key"
          class="filter-chip pressable"
          :class="{ active: moduleFilter === item.key }"
          @tap="selectModule(item.key)"
        >
          {{ item.label }}
        </view>
        <view class="filter-chip format-chip pressable" :class="{ active: fileType }" @tap="chooseFormat">
          <SlidersHorizontal :size="13" />
          <text>{{ fileType ? typeLabel(fileType) : "格式" }}</text>
        </view>
      </view>
    </scroll-view>

    <view class="library-summary">
      <view class="summary-copy">
        <text class="summary-kicker">{{ activeModuleLabel }}</text>
        <text class="summary-text">{{ loading ? "正在整理资料..." : `找到 ${total} 份` }}</text>
      </view>
      <view class="upload-inline pressable" @tap="startUpload">
        <Upload :size="15" />
        <text>放进资料库</text>
      </view>
    </view>

    <scroll-view class="material-scroll" scroll-y @scrolltolower="loadMore">
      <view v-if="materials.length" class="material-list">
        <MaterialRow
          v-for="item in materials"
          :key="item.material_id"
          :material="item"
          :show-module="moduleFilter === 'all'"
          @open="openDetail"
        />
      </view>

      <view v-else-if="!loading" class="empty-library">
        <view class="empty-illustration">
          <Archive :size="31" :stroke-width="1.5" />
          <view class="empty-plus"><Plus :size="13" /></view>
        </view>
        <text class="empty-title">{{ keyword ? "没有找到对应资料" : "资料库还是空的" }}</text>
        <text class="empty-desc">{{ keyword ? "换个说法，或清除筛选再找一次。" : "图片、PDF、表格、文档、音视频，先放进来就能随时翻看。" }}</text>
        <view class="empty-action pressable" @tap="keyword ? clearSearch() : startUpload()">
          {{ keyword ? "清除搜索" : "添加第一份资料" }}
        </view>
      </view>

      <view v-else class="loading-state">
        <LoaderCircle :size="22" class="spin" />
        <text>正在读取资料</text>
      </view>

      <view v-if="materials.length && loadingMore" class="load-more"><LoaderCircle :size="16" class="spin" /><text>继续加载</text></view>
      <view v-if="materials.length && !loadingMore && materials.length >= total" class="list-end">已经翻到最早一份</view>
      <view class="scroll-space"></view>
    </scroll-view>

    <AppTabBar active="materials" />
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad, onPullDownRefresh, onShow, onUnload } from "@dcloudio/uni-app";
import {
  Archive,
  LoaderCircle,
  Mic,
  Plus,
  Search,
  SlidersHorizontal,
  Square,
  Upload,
} from "@lucide/vue";
import AppTabBar from "../../components/AppTabBar.vue";
import MaterialRow from "../../components/MaterialRow.vue";
import { moduleList } from "../../data/modules";
import { dictationAvailable, startDictation } from "../../services/voice";
import {
  chooseFiles,
  chooseImages,
  listMaterials,
  materialTypeLabels,
  uploadMaterial,
} from "../../services/material";
import { ensureBound } from "../../services/session";

const keyword = ref("");
const moduleFilter = ref("all");
const fileType = ref("");
const materials = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 30;
const loading = ref(false);
const loadingMore = ref(false);
const uploading = ref(false);
const listening = ref(false);
const voicePhase = ref("idle");
const voiceInterim = ref("");
let searchTimer = null;
let voiceSession = null;

const moduleFilters = [
  { key: "all", label: "全部" },
  ...moduleList.map((item) => ({ key: item.key, label: item.visual.short })),
];
const activeModuleLabel = computed(() => {
  if (moduleFilter.value === "all") return "TEAM ARCHIVE";
  return moduleList.find((item) => item.key === moduleFilter.value)?.visual.kicker || "MODULE ARCHIVE";
});

function typeLabel(value) {
  return materialTypeLabels[value] || "其他格式";
}

function queueSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadMaterials(true), 360);
}

function clearSearch() {
  keyword.value = "";
  loadMaterials(true);
}

function selectModule(key) {
  moduleFilter.value = key;
  loadMaterials(true);
}

function chooseFormat() {
  uni.showActionSheet({
    itemList: ["全部格式", "图片", "PDF", "表格", "文档", "演示", "文本", "音视频", "其他"],
    success: (result) => {
      const values = ["", "image", "pdf", "excel", "word", "presentation", "text", "video", "other"];
      fileType.value = values[result.tapIndex] || "";
      loadMaterials(true);
    },
  });
}

async function loadMaterials(reset = false) {
  if (loading.value || loadingMore.value) return;
  if (reset) {
    page.value = 1;
    loading.value = true;
  } else {
    loadingMore.value = true;
  }
  try {
    const response = await listMaterials({
      module: moduleFilter.value === "all" ? undefined : moduleFilter.value,
      fileType: fileType.value || undefined,
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      pageSize,
    });
    const incoming = response.items || [];
    materials.value = reset ? incoming : [...materials.value, ...incoming];
    total.value = Number(response.total || 0);
  } catch (error) {
    if (reset) materials.value = [];
    uni.showToast({ title: error.message || "资料加载失败", icon: "none" });
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function loadMore() {
  if (loading.value || loadingMore.value || materials.value.length >= total.value) return;
  page.value += 1;
  loadMaterials(false);
}

function openDetail(material) {
  uni.navigateTo({ url: `/pages/material/index?id=${material.material_id}` });
}

function toggleVoiceSearch() {
  if (listening.value) {
    stopVoiceSearch();
    return;
  }
  if (!dictationAvailable()) {
    uni.showModal({
      title: "当前环境没有语音识别",
      content: "请检查麦克风权限和资料库服务连接，也可以直接输入关键词。",
      showCancel: false,
    });
    return;
  }
  listening.value = true;
  voicePhase.value = "listening";
  voiceInterim.value = "";
  voiceSession = startDictation({
    continuous: false,
    onStateChange: (state) => { voicePhase.value = state; },
    onInterim: (text) => {
      voiceInterim.value = text;
    },
    onFinal: (text) => {
      if (!text.trim()) return;
      keyword.value = text.trim();
      voiceInterim.value = text.trim();
      loadMaterials(true);
    },
    onError: (error) => {
      uni.showToast({ title: error.message || "语音搜索暂不可用", icon: "none" });
    },
    onEnd: () => {
      listening.value = false;
      voicePhase.value = "idle";
      voiceSession = null;
    },
  });
  if (!voiceSession) {
    listening.value = false;
    voicePhase.value = "idle";
  }
}

async function stopVoiceSearch() {
  const session = voiceSession;
  if (!session) return;
  voicePhase.value = "stopping";
  await session.stop?.();
}

async function chooseModuleForUpload() {
  if (moduleFilter.value !== "all") return moduleFilter.value;
  return new Promise((resolve) => {
    uni.showActionSheet({
      itemList: moduleList.map((item) => item.name),
      success: (result) => resolve(moduleList[result.tapIndex].key),
      fail: () => resolve(""),
    });
  });
}

function startUpload() {
  if (uploading.value) return;
  uni.showActionSheet({
    itemList: ["拍照", "从相册选择", "导入任意格式文件"],
    success: async (result) => {
      const module = await chooseModuleForUpload();
      if (!module) return;
      try {
        let files = [];
        if (result.tapIndex === 0) files = await chooseImages({ count: 3, sourceType: ["camera"] });
        else if (result.tapIndex === 1) files = await chooseImages({ count: 9, sourceType: ["album"] });
        else files = await chooseFiles({ count: 9 });
        if (!files.length) return;
        uploading.value = true;
        for (const file of files) {
          await uploadMaterial(file, { module, title: file.name.replace(/\.[^.]+$/, "") });
        }
        moduleFilter.value = module;
        uni.showToast({ title: `已收好 ${files.length} 份资料`, icon: "success" });
        await loadMaterials(true);
      } catch (error) {
        uni.showToast({ title: error.message || error.errMsg || "资料上传失败", icon: "none", duration: 2600 });
      } finally {
        uploading.value = false;
      }
    },
  });
}

onLoad((options) => {
  if (moduleList.some((item) => item.key === options?.module)) moduleFilter.value = options.module;
  loadMaterials(true);
});

onShow(() => {
  if (ensureBound() && materials.value.length) loadMaterials(true);
});

onPullDownRefresh(async () => {
  loading.value = false;
  loadingMore.value = false;
  await loadMaterials(true);
  uni.stopPullDownRefresh();
});

onUnload(() => {
  clearTimeout(searchTimer);
  voiceSession?.abort?.();
});
</script>

<style scoped>
.materials-page {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0 16px;
}
.materials-top {
  flex: none;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-top: calc(18px + env(safe-area-inset-top));
}
.top-copy {
  min-width: 0;
}
.brand-line {
  display: flex;
  align-items: center;
  gap: 6px;
}
.brand-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
}
.brand-name {
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.12em;
}
.page-title {
  display: block;
  margin-top: 8px;
  color: var(--ink);
  font-size: 28px;
  font-weight: 780;
  line-height: 34px;
}
.page-subtitle {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 10px;
}
.upload-button {
  width: 44px;
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 11px;
  border-radius: 50%;
  background: var(--ink);
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(22, 34, 31, 0.16);
}
.search-shell {
  height: 47px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  padding: 0 6px 0 13px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--surface);
}
.search-icon {
  flex: none;
  color: var(--text-muted);
}
.search-input {
  flex: 1;
  min-width: 0;
  height: 45px;
  color: var(--text-primary);
  font-size: 13px;
}
.search-mic {
  width: 36px;
  height: 36px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.search-mic.listening {
  background: var(--warning-bg);
  color: var(--warning);
  animation: soft-pulse 1.8s infinite;
}
.search-mic.stopping {
  animation: none;
  opacity: 0.72;
}
.voice-search-line {
  display: block;
  margin-top: 6px;
  padding: 0 4px;
  color: var(--accent);
  font-size: 9px;
}
.filter-scroll {
  width: 100%;
  margin-top: 12px;
  white-space: nowrap;
}
.filter-row {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding-right: 12px;
}
.filter-chip {
  height: 31px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 600;
}
.filter-chip.active {
  border-color: var(--ink);
  background: var(--ink);
  color: #ffffff;
}
.format-chip {
  color: var(--accent);
}
.format-chip.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-deep);
}
.library-summary {
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.summary-copy {
  min-width: 0;
}
.summary-kicker {
  display: block;
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.1em;
}
.summary-text {
  display: block;
  margin-top: 3px;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 600;
}
.upload-inline {
  min-height: 31px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 9px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--accent);
  font-size: 9px;
  font-weight: 650;
}
.material-scroll {
  flex: 1;
  min-height: 0;
  margin-top: 4px;
}
.material-list {
  padding-bottom: 8px;
}
.empty-library {
  min-height: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 34px 22px;
  text-align: center;
}
.empty-illustration {
  position: relative;
  width: 76px;
  height: 76px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 22px;
  background: var(--surface);
  color: var(--accent);
  box-shadow: var(--shadow-soft);
}
.empty-plus {
  position: absolute;
  right: -2px;
  bottom: 3px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--page-bg);
  border-radius: 50%;
  background: var(--ink);
  color: #ffffff;
}
.empty-title {
  margin-top: 19px;
  color: var(--ink);
  font-size: 17px;
  font-weight: 720;
}
.empty-desc {
  max-width: 280px;
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 17px;
}
.empty-action {
  min-height: 38px;
  display: flex;
  align-items: center;
  margin-top: 18px;
  padding: 0 17px;
  border-radius: 7px;
  background: var(--accent);
  color: #ffffff;
  font-size: 11px;
  font-weight: 650;
}
.loading-state,
.load-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 32px;
  color: var(--text-muted);
  font-size: 10px;
}
.load-more {
  padding: 14px;
}
.list-end {
  padding: 15px;
  color: var(--text-muted);
  font-size: 9px;
  text-align: center;
}
.scroll-space {
  height: calc(12px + env(safe-area-inset-bottom));
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
