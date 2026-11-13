<template>
  <view class="module-page app-page" :class="`tone-${moduleKey}`">
    <PageHeader :title="config.visual.short" fallback="/pages/home/index">
      <template #actions>
        <view class="header-action pressable" @tap="openHistory">全部历史</view>
      </template>
    </PageHeader>

    <scroll-view class="module-scroll" scroll-y>
      <view class="module-hero">
        <view class="hero-grid">
          <view class="hero-top">
            <ModuleMark :module-key="moduleKey" size="lg" />
            <view class="hero-badge">{{ config.visual.kicker }}</view>
          </view>
          <text class="hero-title">{{ config.visual.short }}</text>
          <text class="hero-desc">{{ config.visual.description }}</text>

          <view class="hero-stats">
            <view class="stat-item">
              <text class="stat-value">{{ stats.records }}</text>
              <text class="stat-label">条记录</text>
            </view>
            <view class="stat-item">
              <text class="stat-value">{{ stats.materials }}</text>
              <text class="stat-label">份资料</text>
            </view>
            <view class="stat-item">
              <text class="stat-value">{{ stats.recent }}</text>
              <text class="stat-label">近七日</text>
            </view>
          </view>
        </view>

        <view class="quick-actions">
          <view class="voice-action pressable" @tap="openEntry(true)">
            <view class="voice-icon"><Mic :size="23" /></view>
            <view class="voice-copy">
              <text class="action-kicker">VOICE FIRST</text>
              <text class="action-title">说一条新的</text>
              <text class="action-note">时间、金额、项目都可以直接说</text>
            </view>
            <ArrowUpRight :size="18" class="action-arrow" />
          </view>
          <view class="upload-action pressable" @tap="chooseMaterial">
            <view class="upload-icon"><Plus :size="21" /></view>
            <view class="upload-copy">
              <text class="upload-title">添加资料</text>
              <text class="upload-note">任意格式原件</text>
            </view>
            <LoaderCircle v-if="uploading" :size="17" class="spin" />
            <Upload v-else :size="17" />
          </view>
        </view>
      </view>

      <view class="module-toolbar">
        <view class="toolbar-item pressable" @tap="openHistory">
          <History :size="17" />
          <text>记录归档</text>
          <ChevronRight :size="15" />
        </view>
        <view class="toolbar-item pressable" @tap="openMaterials">
          <Archive :size="17" />
          <text>模块资料库</text>
          <ChevronRight :size="15" />
        </view>
      </view>

      <view class="content-section">
        <view class="section-head">
          <view>
            <text class="section-kicker">RECENT RECORDS</text>
            <text class="section-title">最近留下</text>
          </view>
          <view class="text-link pressable" @tap="openHistory">翻看全部</view>
        </view>

        <view v-if="records.length" class="record-list">
          <view
            v-for="record in records"
            :key="record.record_id"
            class="record-card pressable"
            @tap="openRecord(record)"
          >
            <view class="record-date">
              <text class="date-number">{{ dayOf(record) }}</text>
              <text class="date-month">{{ monthOf(record) }}</text>
            </view>
            <view class="record-main">
              <text class="record-title">{{ recordTitle(moduleKey, record) }}</text>
              <text class="record-summary">{{ recordSummary(record) }}</text>
              <view class="record-meta">
                <text>{{ recordType(record) }}</text>
                <text v-if="materialCount(record.record_id)" class="record-attachment">{{ materialCount(record.record_id) }} 份资料</text>
              </view>
            </view>
            <ChevronRight :size="16" class="record-arrow" />
          </view>
        </view>
        <view v-else-if="!loading" class="empty-panel pressable" @tap="openEntry(true)">
          <view class="empty-mark"><Mic :size="25" /></view>
          <text class="empty-title">这里还没有记录</text>
          <text class="empty-desc">先说说最近听到、看到或正在做的一件事。</text>
          <view class="empty-button">开始说</view>
        </view>
        <view v-else class="loading-panel"><LoaderCircle :size="20" class="spin" /><text>正在整理最近记录</text></view>
      </view>

      <view class="content-section material-block">
        <view class="section-head">
          <view>
            <text class="section-kicker">FILES & MATERIALS</text>
            <text class="section-title">最近资料</text>
          </view>
          <view class="text-link pressable" @tap="openMaterials">资料库</view>
        </view>

        <view v-if="materials.length" class="material-card">
          <MaterialRow
            v-for="item in materials"
            :key="item.material_id"
            :material="item"
            compact
            @open="openMaterialPage"
          />
        </view>
        <view v-else class="material-empty pressable" @tap="chooseMaterial">
          <view class="empty-mark light"><FilePlus2 :size="23" /></view>
          <view class="empty-copy">
            <text class="empty-title">图片、表格、文档都可以</text>
            <text class="empty-desc">先存原文件，之后随时回来查看。</text>
          </view>
          <ChevronRight :size="16" />
        </view>
      </view>

      <view class="module-bottom-space"></view>
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad, onPullDownRefresh, onShow } from "@dcloudio/uni-app";
import {
  Archive,
  ArrowUpRight,
  ChevronRight,
  FilePlus2,
  History,
  LoaderCircle,
  Mic,
  Plus,
  Upload,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import ModuleMark from "../../components/ModuleMark.vue";
import MaterialRow from "../../components/MaterialRow.vue";
import { modules, recordDate, recordTitle } from "../../data/modules";
import { request } from "../../services/api";
import { chooseFiles, chooseImages, listMaterials, uploadMaterial } from "../../services/material";
import { ensureBound } from "../../services/session";

const moduleKey = ref("sale");
const config = computed(() => modules[moduleKey.value]);
const records = ref([]);
const materials = ref([]);
const loading = ref(false);
const uploading = ref(false);
const stats = ref({ records: 0, materials: 0, recent: 0 });
const materialLookup = ref({});

function recordSummary(record) {
  if (moduleKey.value === "sale") {
    return [record.district, record.deal_total_price ? `${record.deal_total_price} 万元` : "", record.buyer]
      .filter((value) => value && !String(value).startsWith("待"))
      .join(" · ") || "项目、价格、买家都可以之后继续补充";
  }
  if (moduleKey.value === "lease") {
    return [record.industry, record.new_project, record.rent_price ? `${record.rent_price} 元/㎡/天` : ""]
      .filter(Boolean)
      .join(" · ");
  }
  if (moduleKey.value === "work") {
    return record.content || [record.related_project, record.follow_status].filter(Boolean).join(" · ");
  }
  return record.content || record.tags || "一条还没有展开的想法";
}

function recordType(record) {
  if (moduleKey.value === "sale") return record.deal_status || "信息待补充";
  if (moduleKey.value === "lease") return record.lease_type || "租赁动态";
  return record.record_type || record.inspiration_type || "记录";
}

function dayOf(record) {
  return recordDate(moduleKey.value, record).slice(8, 10) || "—";
}

function monthOf(record) {
  const value = recordDate(moduleKey.value, record);
  return value ? `${value.slice(5, 7)} 月` : "待补";
}

function materialCount(recordId) {
  return materialLookup.value[recordId] || 0;
}

function openEntry(voice = false) {
  uni.navigateTo({ url: `/pages/entry/index?module=${moduleKey.value}${voice ? "&voice=1" : ""}` });
}

function openHistory() {
  uni.navigateTo({ url: `/pages/history/index?module=${moduleKey.value}` });
}

function openMaterials() {
  uni.navigateTo({ url: `/pages/materials/index?module=${moduleKey.value}` });
}

function openRecord(record) {
  uni.navigateTo({ url: `/pages/detail/index?module=${moduleKey.value}&id=${record.record_id}` });
}

function openMaterialPage(material) {
  uni.navigateTo({ url: `/pages/material/index?id=${material.material_id}` });
}

async function loadModule() {
  if (!ensureBound() || loading.value) return;
  loading.value = true;
  try {
    const [recordResult, materialResult] = await Promise.all([
      request(`/${config.value.endpoint}?page_size=20`),
      listMaterials({ module: moduleKey.value, pageSize: 20 }),
    ]);
    records.value = recordResult.items || [];
    materials.value = materialResult.items || [];
    stats.value.records = Number(recordResult.total || records.value.length);
    stats.value.materials = Number(materialResult.total || materials.value.length);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);
    const cutoffValue = cutoff.toISOString().slice(0, 10);
    stats.value.recent = records.value.filter((record) => recordDate(moduleKey.value, record) >= cutoffValue).length;

    const lookup = {};
    for (const item of materials.value) {
      if (item.record_id) lookup[item.record_id] = (lookup[item.record_id] || 0) + 1;
    }
    materialLookup.value = lookup;
  } catch (error) {
    uni.showToast({ title: error.message || "模块内容加载失败", icon: "none" });
  } finally {
    loading.value = false;
  }
}

async function chooseMaterial() {
  if (uploading.value) return;
  uni.showActionSheet({
    itemList: ["拍照或从相册选择", "导入任意格式文件"],
    success: async (result) => {
      try {
        const files = result.tapIndex === 0
          ? await chooseImages({ count: 9, sourceType: ["album", "camera"] })
          : await chooseFiles({ count: 9 });
        if (!files.length) return;
        uploading.value = true;
        for (const file of files) {
          await uploadMaterial(file, { module: moduleKey.value, title: file.name.replace(/\.[^.]+$/, "") });
        }
        uni.showToast({ title: `已收好 ${files.length} 份资料`, icon: "success" });
        await loadModule();
      } catch (error) {
        uni.showToast({ title: error.message || error.errMsg || "资料上传失败", icon: "none", duration: 2600 });
      } finally {
        uploading.value = false;
      }
    },
  });
}

onLoad((options) => {
  if (modules[options?.module]) moduleKey.value = options.module;
  loadModule();
});

onShow(() => {
  if (ensureBound()) loadModule();
});

onPullDownRefresh(async () => {
  loading.value = false;
  await loadModule();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
.module-page {
  height: 100vh;
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
.module-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.module-hero {
  margin: 4px 16px 0;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.tone-sale .module-hero {
  border-color: #ecd2c9;
  background: #fffaf8;
}
.tone-lease .module-hero {
  border-color: #cbe2dc;
  background: #f7fffc;
}
.tone-work .module-hero {
  border-color: #d1dceb;
  background: #f8faff;
}
.tone-inspiration .module-hero {
  border-color: #e9d4db;
  background: #fff9fb;
}
.hero-grid {
  min-width: 0;
}
.hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.hero-badge {
  padding: 4px 7px;
  border: 1px solid rgba(28, 40, 37, 0.08);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.65);
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.08em;
}
.hero-title {
  display: block;
  margin-top: 15px;
  color: var(--ink);
  font-size: 27px;
  font-weight: 780;
  line-height: 33px;
}
.hero-desc {
  display: block;
  max-width: 290px;
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 17px;
}
.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 18px;
  padding: 12px 0;
  border-top: 1px solid rgba(28, 40, 37, 0.08);
  border-bottom: 1px solid rgba(28, 40, 37, 0.08);
}
.stat-item {
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding-left: 12px;
  border-left: 1px solid rgba(28, 40, 37, 0.08);
}
.stat-item:first-child {
  padding-left: 0;
  border-left: 0;
}
.stat-value {
  color: var(--ink);
  font-size: 22px;
  font-weight: 760;
  line-height: 26px;
}
.stat-label {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 9px;
}
.quick-actions {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 9px;
  margin-top: 14px;
}
.voice-action {
  min-height: 108px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 13px;
  border-radius: 9px;
  background: var(--ink);
  color: #ffffff;
}
.voice-icon {
  width: 41px;
  height: 41px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(167, 238, 222, 0.34);
  border-radius: 50%;
  background: rgba(129, 225, 205, 0.1);
  color: #bff4e8;
}
.voice-copy {
  flex: 1;
  min-width: 0;
}
.action-kicker {
  display: block;
  color: #8ed8c8;
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.09em;
}
.action-title {
  display: block;
  margin-top: 8px;
  font-size: 15px;
  font-weight: 700;
}
.action-note {
  display: block;
  margin-top: 4px;
  color: #abc3bc;
  font-size: 8px;
  line-height: 13px;
}
.action-arrow {
  flex: none;
  margin-top: 1px;
  color: #a7c9c0;
}
.upload-action {
  min-height: 108px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 13px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--accent);
}
.upload-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-soft);
}
.upload-copy {
  margin-top: auto;
}
.upload-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
}
.upload-note {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 8px;
}
.module-toolbar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
  margin: 11px 16px 0;
}
.toolbar-item {
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 600;
}
.toolbar-item :last-child {
  margin-left: auto;
  color: var(--text-muted);
}
.content-section {
  margin: 24px 16px 0;
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
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.1em;
}
.section-title {
  color: var(--ink);
  font-size: 18px;
  font-weight: 730;
  line-height: 24px;
}
.text-link {
  min-height: 32px;
  display: flex;
  align-items: center;
  color: var(--accent);
  font-size: 11px;
  font-weight: 650;
}
.record-list,
.material-card {
  margin-top: 9px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.record-card {
  min-height: 84px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid var(--border);
}
.record-card:last-child {
  border-bottom: 0;
}
.record-date {
  width: 42px;
  height: 48px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: var(--surface-soft);
}
.record-date .date-number {
  color: var(--ink);
  font-size: 18px;
  font-weight: 750;
  line-height: 21px;
}
.record-date .date-month {
  color: var(--text-muted);
  font-size: 8px;
}
.record-main {
  flex: 1;
  min-width: 0;
}
.record-title {
  display: block;
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
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 10px;
  line-height: 16px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.record-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 8px;
}
.record-attachment {
  padding-left: 7px;
  border-left: 1px solid var(--border);
  color: var(--accent);
}
.record-arrow {
  flex: none;
  color: var(--text-muted);
}
.material-block {
  margin-bottom: 22px;
}
.material-card {
  padding: 0 12px;
}
.empty-panel,
.loading-panel,
.material-empty {
  min-height: 126px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: 9px;
  padding: 18px;
  border: 1px dashed #cfdcd7;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.54);
  text-align: center;
}
.empty-mark {
  width: 47px;
  height: 47px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.empty-mark.light {
  width: 43px;
  height: 43px;
  flex: none;
  border-radius: 9px;
}
.empty-title {
  display: block;
  margin-top: 10px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}
.empty-desc {
  display: block;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 15px;
}
.empty-button {
  min-height: 31px;
  display: flex;
  align-items: center;
  margin-top: 11px;
  padding: 0 13px;
  border-radius: 6px;
  background: var(--accent);
  color: #ffffff;
  font-size: 10px;
  font-weight: 650;
}
.loading-panel {
  flex-direction: row;
  gap: 8px;
  color: var(--text-muted);
  font-size: 10px;
}
.material-empty {
  min-height: 82px;
  flex-direction: row;
  justify-content: flex-start;
  gap: 10px;
  text-align: left;
}
.material-empty .empty-copy {
  flex: 1;
  min-width: 0;
}
.material-empty .empty-title {
  margin-top: 0;
}
.module-bottom-space {
  height: calc(28px + env(safe-area-inset-bottom));
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
