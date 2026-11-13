<template>
  <view class="material-row pressable" :class="{ compact }" @tap="$emit('open', material)">
    <view class="file-icon" :class="`type-${material.file_type}`">
      <component :is="fileIcon" :size="compact ? 18 : 21" :stroke-width="1.9" />
    </view>
    <view class="file-main">
      <view class="file-title-line">
        <text class="file-title">{{ material.title || material.file_name }}</text>
        <text v-if="showModule" class="module-tag" :class="`module-${material.module}`">{{ moduleShort }}</text>
      </view>
      <text v-if="!compact" class="file-meta">{{ typeLabel }} · {{ formatSize(material.file_size) }} · {{ formatDate(material.upload_time) }}</text>
      <text v-else class="file-meta">{{ typeLabel }} · {{ formatDate(material.upload_time) }}</text>
      <text v-if="!compact && material.extracted_text_preview" class="file-preview line-clamp-2">{{ material.extracted_text_preview }}</text>
      <view v-if="!compact" class="status-line">
        <view class="status-dot" :class="`status-${material.extraction_status}`"></view>
        <text>{{ statusLabel }}</text>
      </view>
    </view>
    <ChevronRight class="chevron" :size="17" />
  </view>
</template>

<script setup>
import { computed } from "vue";
import {
  ChevronRight,
  FileArchive,
  FileAudio,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileVideo,
  Presentation,
} from "@lucide/vue";

const props = defineProps({
  material: { type: Object, required: true },
  compact: { type: Boolean, default: false },
  showModule: { type: Boolean, default: false },
});

defineEmits(["open"]);

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
const labels = {
  image: "图片",
  pdf: "PDF",
  excel: "表格",
  csv: "CSV",
  word: "文档",
  presentation: "演示",
  text: "文本",
  audio: "音频",
  video: "视频",
  archive: "压缩包",
  other: "其他文件",
};
const statusLabels = {
  extracted: "已提取正文",
  stored: "已安全存放",
  unavailable: "原件已存，待配置识别",
  failed: "原件已存，提取失败",
};
const moduleNames = {
  sale: "买卖",
  lease: "租赁",
  work: "工作",
  inspiration: "灵感",
};
const fileIcon = computed(() => icons[props.material.file_type] || FileText);
const typeLabel = computed(() => labels[props.material.file_type] || "文件");
const statusLabel = computed(() => statusLabels[props.material.extraction_status] || "已安全存放");
const moduleShort = computed(() => moduleNames[props.material.module] || "");

function formatSize(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value) {
  return String(value || "").slice(0, 10);
}
</script>

<style scoped>
.material-row {
  min-height: 82px;
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 13px 0;
  border-bottom: 1px solid var(--border);
}
.material-row:last-child {
  border-bottom: 0;
}
.material-row.compact {
  min-height: 62px;
  align-items: center;
  padding: 9px 0;
}
.file-icon {
  width: 42px;
  height: 42px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--soft);
  color: var(--text-secondary);
}
.compact .file-icon {
  width: 34px;
  height: 34px;
}
.type-pdf,
.type-word {
  background: #f8e8e5;
  color: #a44e42;
}
.type-excel,
.type-csv {
  background: #e4f2e9;
  color: #2d7c4f;
}
.type-image {
  background: var(--work-soft);
  color: var(--work);
}
.type-audio,
.type-video {
  background: var(--inspiration-soft);
  color: var(--inspiration);
}
.file-main {
  flex: 1;
  min-width: 0;
}
.file-title-line {
  display: flex;
  align-items: center;
  gap: 6px;
}
.file-title {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 650;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.compact .file-title {
  font-size: 13px;
  font-weight: 600;
}
.module-tag {
  flex: none;
  padding: 2px 5px;
  border-radius: 4px;
  background: var(--soft);
  color: var(--text-secondary);
  font-size: 9px;
  font-weight: 700;
}
.module-sale {
  background: var(--sale-soft);
  color: var(--sale);
}
.module-lease {
  background: var(--lease-soft);
  color: var(--lease);
}
.module-work {
  background: var(--work-soft);
  color: var(--work);
}
.module-inspiration {
  background: var(--inspiration-soft);
  color: var(--inspiration);
}
.file-meta {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 16px;
}
.file-preview {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 17px;
}
.status-line {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 10px;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}
.status-extracted {
  background: var(--accent);
}
.status-unavailable,
.status-failed {
  background: var(--warning);
}
.chevron {
  flex: none;
  margin-top: 10px;
  color: var(--text-muted);
}
.compact .chevron {
  margin-top: 0;
}
</style>
