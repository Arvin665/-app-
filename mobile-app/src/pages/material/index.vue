<template>
  <view class="material-page app-page">
    <PageHeader title="资料详情" fallback="/pages/materials/index">
      <template #actions>
        <view v-if="material?.can_delete" class="header-action pressable" @tap="removeMaterial">删除</view>
      </template>
    </PageHeader>

    <scroll-view class="detail-scroll" scroll-y>
      <view v-if="material" class="detail-content">
        <StatusNotice v-if="actionError" tone="error" title="这次操作没有完成" :message="actionError" closeable @close="actionError = ''" />
        <StatusNotice v-if="linkedRecordError" tone="warning" title="关联记录暂未加载" :message="linkedRecordError" compact />
        <view class="file-hero" :class="`type-${material.file_type}`">
          <view class="hero-backdrop"></view>
          <view class="file-mark"><component :is="fileIcon" :size="31" :stroke-width="1.7" /></view>
          <text class="file-title">{{ material.title || material.file_name }}</text>
          <text class="file-name">{{ material.file_name }}</text>
          <view class="file-meta-row">
            <text>{{ typeLabel }}</text>
            <view class="meta-dot"></view>
            <text>{{ formatFileSize(material.file_size) }}</text>
            <view class="meta-dot"></view>
            <text>{{ moduleName }}</text>
          </view>
          <view class="hero-actions">
            <button class="open-button pressable" @tap="openOriginal">
              <ExternalLink :size="17" />
              <text>打开原件</text>
            </button>
            <button v-if="material.record_id" class="record-button pressable" @tap="openLinkedRecord">
              <Link2 :size="17" />
              <text>关联记录</text>
            </button>
          </view>
        </view>

        <image
          v-if="material.file_type === 'image' && material.file_url"
          class="image-preview"
          :src="material.file_url"
          mode="widthFix"
          @tap="openOriginal"
        />

        <view class="status-card" :class="`status-${material.extraction_status}`">
          <view class="status-head">
            <view class="status-mark"><ScanText :size="19" /></view>
            <view class="status-copy">
              <text class="status-title">{{ statusLabel }}</text>
              <text class="status-note">{{ material.extraction_note || "原件已安全存放。" }}</text>
            </view>
            <text class="status-badge">{{ extractionBadge }}</text>
          </view>
          <view v-if="material.has_extracted_text" class="status-stats">
            <view><text class="stat-value">{{ extractedText.length }}</text><text class="stat-label">正文字符</text></view>
            <view><text class="stat-value">{{ extractedFieldList.length }}</text><text class="stat-label">识别字段</text></view>
            <view><text class="stat-value">{{ material.metadata?.pages || material.metadata?.rows || "—" }}</text><text class="stat-label">{{ contentUnit }}</text></view>
          </view>
        </view>

        <view v-if="extractedFieldList.length" class="section-card">
          <view class="section-head">
            <text class="section-title">识别出的字段</text>
            <text class="section-kicker">STRUCTURED</text>
          </view>
          <view class="field-grid">
            <view v-for="item in extractedFieldList" :key="item.key" class="field-chip">
              <text class="field-label">{{ item.label }}</text>
              <text class="field-value">{{ item.value }}</text>
            </view>
          </view>
        </view>

        <view v-if="material.has_extracted_text" class="section-card">
          <view class="section-head">
            <text class="section-title">可检索正文</text>
            <view class="copy-action pressable" @tap="copyText"><Copy :size="15" /><text>复制</text></view>
          </view>
          <scroll-view class="text-preview" scroll-y>
            <text class="extracted-text">{{ extractedText }}</text>
          </scroll-view>
        </view>

        <view v-else class="section-card unavailable-card">
          <view class="unavailable-icon"><FileLock2 :size="23" /></view>
          <view class="unavailable-copy">
            <text class="unavailable-title">原件已完整保存</text>
            <text class="unavailable-desc">当前格式暂时没有正文提取结果，不影响打开、下载和继续关联记录。</text>
          </view>
        </view>

        <view class="section-card">
          <view class="section-head">
            <text class="section-title">文件信息</text>
            <text class="section-kicker">DETAILS</text>
          </view>
          <view class="info-grid">
            <view class="info-row"><text class="info-label">所属模块</text><text class="info-value">{{ moduleName }}</text></view>
            <view class="info-row"><text class="info-label">文件格式</text><text class="info-value">{{ material.file_type?.toUpperCase() }}</text></view>
            <view class="info-row"><text class="info-label">上传时间</text><text class="info-value">{{ formatDate(material.upload_time) }}</text></view>
            <view class="info-row"><text class="info-label">文件大小</text><text class="info-value">{{ formatFileSize(material.file_size) }}</text></view>
            <view class="info-row"><text class="info-label">原始文件名</text><text class="info-value">{{ material.file_name }}</text></view>
            <view class="info-row"><text class="info-label">关联记录</text><text class="info-value">{{ linkedRecordTitle || (material.record_id ? material.record_id : "尚未关联") }}</text></view>
          </view>
        </view>

        <button v-if="material.can_delete" class="delete-button pressable" @tap="removeMaterial">
          <Trash2 :size="17" />
          <text>从资料库删除这份资料</text>
        </button>
        <view class="page-space"></view>
      </view>

      <StatePanel v-else-if="loading" state="loading" title="正在读取资料" description="正在读取原件信息、正文提取状态和关联记录。" />
      <StatePanel
        v-else
        state="error"
        title="资料暂时没有加载出来"
        :description="loadError || '资料可能已经删除，或者当前设备没有访问权限。'"
        action-text="重新加载"
        secondary-text="返回资料库"
        @action="loadMaterial"
        @secondary="backToMaterials"
      />
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import {
  Copy,
  ExternalLink,
  FileArchive,
  FileAudio,
  FileImage,
  FileLock2,
  FileSpreadsheet,
  FileText,
  FileVideo,
  Link2,
  Presentation,
  ScanText,
  Trash2,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import StatePanel from "../../components/StatePanel.vue";
import StatusNotice from "../../components/StatusNotice.vue";
import { modules, recordTitle } from "../../data/modules";
import { request } from "../../services/api";
import {
  deleteMaterial,
  extractionLabels,
  formatFileSize,
  getMaterial,
  materialTypeLabels,
  openMaterial,
} from "../../services/material";
import { ensureBound } from "../../services/session";

const materialId = ref("");
const material = ref(null);
const linkedRecord = ref(null);
const loading = ref(true);
const loadError = ref("");
const actionError = ref("");
const linkedRecordError = ref("");

const icons = {
  image: FileImage,
  pdf: FileText,
  excel: FileSpreadsheet,
  csv: FileSpreadsheet,
  word: FileText,
  presentation: Presentation,
  text: FileText,
  audio: FileAudio,
  video: FileVideo,
  archive: FileArchive,
  other: FileText,
};
const fileIcon = computed(() => icons[material.value?.file_type] || FileText);
const typeLabel = computed(() => materialTypeLabels[material.value?.file_type] || "其他文件");
const statusLabel = computed(() => extractionLabels[material.value?.extraction_status] || "原件已安全存放");
const extractionBadge = computed(() => {
  if (material.value?.extraction_status === "extracted") return "可搜索";
  if (material.value?.extraction_status === "unavailable") return "原样保存";
  if (material.value?.extraction_status === "failed") return "提取异常";
  return "已归档";
});
const moduleName = computed(() => modules[material.value?.module]?.visual?.short || material.value?.module || "");
const extractedText = computed(() => String(material.value?.extracted_text || ""));
const contentUnit = computed(() => {
  if (material.value?.metadata?.pages) return "页";
  if (material.value?.metadata?.rows) return "行";
  if (material.value?.metadata?.slides) return "页";
  return "项";
});
const extractedFieldList = computed(() => {
  const fields = material.value?.extracted_fields || {};
  const config = modules[material.value?.module];
  if (!config) return [];
  return Object.entries(fields)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "")
    .map(([key, value]) => ({
      key,
      label: config.fields.find((field) => field.key === key)?.label || key,
      value: String(value),
    }));
});
const linkedRecordTitle = computed(() => {
  if (!linkedRecord.value) return "";
  return recordTitle(material.value.module, linkedRecord.value);
});

function formatDate(value) {
  return String(value || "").replace("T", " ").slice(0, 16);
}

async function openOriginal() {
  actionError.value = "";
  if (!material.value?.file_url) {
    actionError.value = "这份资料没有可打开的原件地址，请稍后重新上传。";
    return;
  }
  try {
    await openMaterial(material.value, { openExternally: true });
  } catch (error) {
    actionError.value = error.message || "原件暂时无法打开，请检查网络后重试。";
  }
}

function openLinkedRecord() {
  if (!material.value?.record_id) return;
  uni.navigateTo({
    url: `/pages/detail/index?module=${material.value.module}&id=${material.value.record_id}`,
  });
}

function copyText() {
  uni.setClipboardData({
    data: extractedText.value,
    success: () => uni.showToast({ title: "正文已复制", icon: "success" }),
    fail: () => { actionError.value = "正文没有复制成功，请重试。"; },
  });
}

function removeMaterial() {
  actionError.value = "";
  if (!material.value?.material_id) return;
  uni.showModal({
    title: "删除资料",
    content: "删除后资料将不再出现在资料库中。",
    confirmColor: "#b64c46",
    success: async (result) => {
      if (!result.confirm) return;
      try {
        await deleteMaterial(material.value.material_id);
        uni.showToast({ title: "资料已删除", icon: "success" });
        setTimeout(() => uni.navigateBack(), 400);
      } catch (error) {
        actionError.value = error.message || "删除失败，请检查网络后重试。";
      }
    },
  });
}

async function loadMaterial() {
  loading.value = true;
  loadError.value = "";
  actionError.value = "";
  linkedRecordError.value = "";
  try {
    material.value = await getMaterial(materialId.value);
    if (material.value.record_id && modules[material.value.module]) {
      try {
        linkedRecord.value = await request(`/${modules[material.value.module].endpoint}/${material.value.record_id}`);
      } catch (error) {
        linkedRecord.value = null;
        linkedRecordError.value = "原件已经加载，但关联记录标题暂时没有同步。你仍可以打开原件或返回资料库。";
      }
    }
  } catch (error) {
    material.value = null;
    loadError.value = error.message || "资料加载失败，请检查网络和资料库服务。";
  } finally {
    loading.value = false;
  }
}

function backToMaterials() {
  uni.navigateBack({ fail: () => uni.reLaunch({ url: "/pages/materials/index" }) });
}

onLoad((options) => {
  if (!ensureBound()) return;
  materialId.value = options?.id || "";
  loadMaterial();
});
</script>

<style scoped>
.detail-content :deep(.status-notice) {
  margin-left: 0;
  margin-right: 0;
}
.material-page {
  height: 100vh;
  overflow: hidden;
}
.header-action {
  min-height: 32px;
  display: flex;
  align-items: center;
  padding: 0 7px;
  color: var(--danger);
  font-size: 12px;
  font-weight: 650;
}
.detail-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.detail-content {
  padding: 4px 16px 0;
}
.file-hero {
  position: relative;
  overflow: hidden;
  padding: 20px 18px 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.hero-backdrop {
  position: absolute;
  top: -38px;
  right: -30px;
  width: 130px;
  height: 130px;
  border-radius: 50%;
  background: var(--surface-soft);
  opacity: 0.7;
}
.file-mark {
  position: relative;
  width: 58px;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--accent-soft);
  color: var(--accent);
}
.type-pdf .file-mark,
.type-word .file-mark {
  background: #f8e8e5;
  color: #a44e42;
}
.type-excel .file-mark,
.type-csv .file-mark {
  background: #e4f2e9;
  color: #2d7c4f;
}
.type-image .file-mark {
  background: var(--work-soft);
  color: var(--work);
}
.type-audio .file-mark,
.type-video .file-mark {
  background: var(--inspiration-soft);
  color: var(--inspiration);
}
.file-title {
  position: relative;
  display: block;
  margin-top: 18px;
  color: var(--ink);
  font-size: 22px;
  font-weight: 760;
  line-height: 29px;
  word-break: break-word;
}
.file-name {
  position: relative;
  display: block;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 15px;
  word-break: break-all;
}
.file-meta-row {
  position: relative;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 9px;
}
.meta-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--border);
}
.hero-actions {
  position: relative;
  display: flex;
  gap: 8px;
  margin-top: 18px;
}
.open-button,
.record-button {
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 650;
}
.open-button {
  flex: 1.2;
  background: var(--ink);
  color: #ffffff;
}
.record-button {
  flex: 1;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-primary);
}
.image-preview {
  width: 100%;
  max-height: 420px;
  margin-top: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.status-card,
.section-card {
  margin-top: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.status-card {
  padding: 14px;
}
.status-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.status-mark {
  width: 38px;
  height: 38px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--accent-soft);
  color: var(--accent);
}
.status-unavailable .status-mark,
.status-failed .status-mark {
  background: var(--warning-bg);
  color: var(--warning);
}
.status-copy {
  flex: 1;
  min-width: 0;
}
.status-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
}
.status-note {
  display: block;
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
}
.status-badge {
  flex: none;
  padding: 3px 6px;
  border-radius: 4px;
  background: var(--surface-soft);
  color: var(--text-secondary);
  font-size: 8px;
  font-weight: 700;
}
.status-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 13px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.status-stats > view {
  padding-left: 12px;
  border-left: 1px solid var(--border);
}
.status-stats > view:first-child {
  padding-left: 0;
  border-left: 0;
}
.stat-value {
  display: block;
  color: var(--ink);
  font-size: 17px;
  font-weight: 740;
}
.stat-label {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 8px;
}
.section-card {
  padding: 15px;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.section-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 700;
}
.section-kicker {
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.09em;
}
.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}
.field-chip {
  min-width: 0;
  padding: 9px 10px;
  border-radius: 7px;
  background: #f6f8f7;
}
.field-label {
  display: block;
  color: var(--text-muted);
  font-size: 8px;
}
.field-value {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 600;
  line-height: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.copy-action {
  min-height: 30px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--accent);
  font-size: 9px;
}
.text-preview {
  height: 230px;
  margin-top: 12px;
  padding: 12px;
  border-radius: 7px;
  background: #f7f9f8;
}
.extracted-text {
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 19px;
  white-space: pre-wrap;
}
.unavailable-card {
  display: flex;
  align-items: center;
  gap: 11px;
}
.unavailable-icon {
  width: 43px;
  height: 43px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: var(--warning-bg);
  color: var(--warning);
}
.unavailable-copy {
  flex: 1;
  min-width: 0;
}
.unavailable-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}
.unavailable-desc {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 15px;
}
.info-grid {
  margin-top: 9px;
}
.info-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 9px 0;
  border-top: 1px solid var(--border);
}
.info-label {
  width: 78px;
  flex: none;
  color: var(--text-muted);
  font-size: 9px;
}
.info-value {
  flex: 1;
  color: var(--text-primary);
  font-size: 10px;
  line-height: 16px;
  text-align: right;
  word-break: break-all;
}
.delete-button {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 16px;
  border: 1px solid #ebd5d1;
  border-radius: 8px;
  background: #fff8f6;
  color: var(--danger);
  font-size: 11px;
  font-weight: 600;
}
.loading-page {
  min-height: 70vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--text-muted);
  font-size: 11px;
}
.page-space {
  height: calc(24px + env(safe-area-inset-bottom));
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
