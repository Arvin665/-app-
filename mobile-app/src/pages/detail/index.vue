<template>
  <view class="detail-page">
    <PageHeader title="记录详情" fallback="/pages/history/index">
      <template #actions>
        <text class="header-action" @tap="editRecord">编辑</text>
      </template>
    </PageHeader>

    <scroll-view class="detail-scroll" scroll-y>
      <view v-if="record" class="content">
        <view class="hero-card">
          <text class="record-title">{{ title }}</text>
          <text class="record-subtitle">{{ config.name }} · {{ businessDate }} · {{ subtitle }}</text>
          <view class="field-list">
            <view v-for="field in visibleFields" :key="field.key" class="field-row">
              <text class="field-label">{{ field.label }}</text>
              <text class="field-value" :class="{ muted: !hasValue(record[field.key]) }">
                {{ displayValue(field) || "未填写" }}
              </text>
            </view>
          </view>
        </view>

        <view v-if="attachmentList.length" class="section-card">
          <text class="section-title">附件</text>
          <view v-for="file in attachmentList" :key="file.attach_id" class="attachment-row" @tap="openAttachment(file)">
            <view class="attachment-icon">{{ file.file_type === "image" ? "图" : "文" }}</view>
            <view class="attachment-info">
              <text class="attachment-name">{{ file.file_name }}</text>
              <text class="attachment-meta">{{ formatSize(file.file_size) }} · {{ file.upload_time?.slice(0, 10) }}</text>
            </view>
            <text class="attachment-open">预览</text>
          </view>
        </view>

        <view v-if="canShowShare" class="section-card share-card">
          <view>
            <text class="share-title">团队共享</text>
            <text class="share-desc">{{ record.is_shared ? "当前记录已对团队可见" : "当前记录仅本人可见" }}</text>
          </view>
          <switch :checked="Boolean(record.is_shared)" color="#165DFF" @change="toggleShared" />
        </view>

        <view class="bottom-actions safe-bottom">
          <button class="secondary-button edit-button" @tap="editRecord">编辑记录</button>
          <button class="text-button delete-button" @tap="deleteRecord">删除</button>
        </view>
      </view>
      <view v-else class="empty-state">{{ loading ? "加载中..." : "记录不存在或无权限访问" }}</view>
      <view class="scroll-space"></view>
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import PageHeader from "../../components/PageHeader.vue";
import { request } from "../../services/api";
import { getCachedRecords } from "../../services/localDb";
import { getSession } from "../../services/session";
import { modules, recordDate, recordTitle } from "../../data/modules";

const moduleKey = ref("sale");
const config = computed(() => modules[moduleKey.value]);
const record = ref(null);
const attachmentList = ref([]);
const loading = ref(true);
const recordId = ref("");
const statusMap = { 0: "未做", 1: "正在做", 2: "已做好", 3: "计划搁置" };

const title = computed(() => (record.value ? recordTitle(moduleKey.value, record.value) : ""));
const businessDate = computed(() => (record.value ? recordDate(moduleKey.value, record.value) : ""));
const subtitle = computed(() => {
  if (!record.value) return "";
  if (moduleKey.value === "sale") return record.value.deal_status || "";
  if (moduleKey.value === "lease") return record.value.lease_type || "";
  if (moduleKey.value === "work") return record.value.record_type || "";
  return record.value.inspiration_type || "";
});
const visibleFields = computed(() =>
  config.value.fields.filter((field) => {
    if (field.adminOnly && getSession()?.role_level !== 1) return false;
    if (field.key === "commission_remark" && !record.value?.[field.key]) return false;
    return field.core || hasValue(record.value?.[field.key]);
  }),
);
const canShowShare = computed(() => moduleKey.value === "work" && record.value?.record_type !== "每日复盘");

function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function displayValue(field) {
  const value = record.value?.[field.key];
  if (field.key === "is_shared") return Number(value) ? "团队共享" : "仅本人可见";
  if (field.key === "ext_field_5") return statusMap[Number(value)] || "未做";
  if (field.type === "switch") return Number(value) ? "是" : "否";
  return value ? `${value}${field.unit ? ` ${field.unit}` : ""}` : "";
}

function formatSize(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function loadDetail() {
  loading.value = true;
  try {
    record.value = await request(`/${config.value.endpoint}/${recordId.value}`);
    try {
      const attachmentResponse = await request(
        `/attachments?biz_type=${moduleKey.value}&biz_id=${recordId.value}`,
      );
      attachmentList.value = attachmentResponse.items || [];
    } catch (error) {
      attachmentList.value = [];
    }
  } catch (error) {
    record.value = (await getCachedRecords(moduleKey.value)).find((item) => item.record_id === recordId.value) || null;
    if (!record.value) uni.showToast({ title: error.message || "记录加载失败", icon: "none" });
  } finally {
    loading.value = false;
  }
}

function editRecord() {
  if (!recordId.value) return;
  uni.navigateTo({ url: `/pages/entry/index?module=${moduleKey.value}&id=${recordId.value}` });
}

async function toggleShared(event) {
  const next = event.detail.value ? 1 : 0;
  try {
    const updated = await request(`/work-logs/${recordId.value}`, { method: "PATCH", data: { is_shared: next } });
    record.value = updated;
    uni.showToast({ title: next ? "已设为团队共享" : "已设为仅本人可见", icon: "success" });
  } catch (error) {
    uni.showToast({ title: error.message || "设置失败", icon: "none" });
  }
}

async function openAttachment(file) {
  const url = file.file_url;
  if (file.file_type === "image") {
    uni.previewImage({ urls: [url], current: url });
    return;
  }
  uni.showLoading({ title: "正在打开" });
  uni.downloadFile({
    url,
    success: (result) => {
      if (result.statusCode === 200) {
        uni.openDocument({ filePath: result.tempFilePath, showMenu: true });
      } else {
        uni.showToast({ title: "附件下载失败", icon: "none" });
      }
    },
    fail: () => uni.showToast({ title: "附件下载失败", icon: "none" }),
    complete: () => uni.hideLoading(),
  });
}

function deleteRecord() {
  uni.showModal({
    title: "删除记录",
    content: "记录将进入回收站并保留 7 天。",
    confirmColor: "#FF7D00",
    success: async (result) => {
      if (!result.confirm) return;
      try {
        await request(`/${config.value.endpoint}/${recordId.value}`, { method: "DELETE" });
        uni.showToast({ title: "已移入回收站", icon: "success" });
        setTimeout(() => uni.navigateBack(), 500);
      } catch (error) {
        uni.showToast({ title: error.message || "删除失败", icon: "none" });
      }
    },
  });
}

onLoad((options) => {
  if (modules[options?.module]) moduleKey.value = options.module;
  recordId.value = options?.id || "";
  loadDetail();
});
</script>

<style scoped>
.detail-page {
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
.detail-scroll {
  flex: 1;
  min-height: 0;
}
.content {
  padding: 0 16px env(safe-area-inset-bottom);
}
.hero-card,
.section-card {
  margin-bottom: 12px;
  border-radius: 8px;
  background: var(--surface);
}
.hero-card {
  padding: 16px;
}
.record-title {
  display: block;
  font-size: 18px;
  font-weight: 600;
  line-height: 26px;
}
.record-subtitle {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 12px;
}
.field-list {
  margin-top: 12px;
}
.field-row {
  min-height: 40px;
  display: flex;
  align-items: flex-start;
  padding: 9px 0;
  border-top: 1px solid var(--border);
}
.field-label {
  width: 112px;
  flex: none;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 20px;
}
.field-value {
  flex: 1;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 20px;
  white-space: pre-wrap;
}
.field-value.muted {
  color: var(--text-muted);
}
.section-card {
  padding: 16px;
}
.section-title {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
}
.attachment-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
}
.attachment-icon {
  width: 40px;
  height: 40px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: var(--page-bg);
  color: var(--text-muted);
  font-size: 12px;
}
.attachment-info {
  flex: 1;
  min-width: 0;
}
.attachment-name {
  display: block;
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attachment-meta {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 11px;
}
.attachment-open {
  flex: none;
  color: var(--accent);
  font-size: 11px;
}
.share-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.share-title,
.share-desc {
  display: block;
}
.share-title {
  font-size: 14px;
  font-weight: 600;
}
.share-desc {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 11px;
}
.bottom-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}
.edit-button {
  flex: 1;
}
.delete-button {
  width: 88px;
  height: 44px;
  color: var(--warning);
  line-height: 44px;
}
.scroll-space {
  height: 24px;
}
</style>
