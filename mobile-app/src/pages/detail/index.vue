<template>
  <view class="detail-page app-page" :class="`tone-${moduleKey}`">
    <PageHeader title="记录详情" :fallback="`/pages/history/index?module=${moduleKey}`">
      <template #actions>
        <view v-if="record?.can_edit" class="header-action pressable" @tap="editRecord">补充编辑</view>
      </template>
    </PageHeader>

    <scroll-view class="detail-scroll" scroll-y>
      <view v-if="record" class="detail-content">
        <view class="record-hero">
          <view class="hero-head">
            <ModuleMark :module-key="moduleKey" size="lg" />
            <view class="hero-meta">
              <text class="hero-kicker">{{ config.visual.kicker }}</text>
              <text class="hero-date">{{ businessDate || "日期待补充" }}</text>
            </view>
          </view>
          <text class="record-title">{{ title }}</text>
          <view class="hero-badges">
            <text class="hero-badge">{{ subtitle || "信息待补充" }}</text>
            <text v-if="moduleKey === 'work'" class="hero-badge">{{ record.is_shared ? "团队共享" : "仅本人可见" }}</text>
            <text v-if="record.tags" class="hero-badge">{{ record.tags }}</text>
          </view>
          <view class="hero-actions">
            <button v-if="record.can_edit" class="edit-button pressable" @tap="editRecord">
              <Pencil :size="16" />
              <text>继续补充</text>
            </button>
            <button class="add-file-button pressable" @tap="chooseMaterial">
              <Paperclip :size="17" />
              <text>添加资料</text>
            </button>
          </view>
        </view>

        <StatusNotice
          v-if="cacheNotice"
          tone="warning"
          title="正在显示本机缓存"
          :message="cacheNotice"
          action-text="重新连接"
          @action="loadDetail"
        />
        <StatusNotice
          v-if="actionError"
          tone="error"
          title="这次操作没有完成"
          :message="actionError"
          closeable
          @close="actionError = ''"
        />

        <view class="section-card">
          <view class="section-head">
            <view>
              <text class="section-kicker">RECORD FIELDS</text>
              <text class="section-title">记录内容</text>
            </view>
            <text class="field-total">{{ visibleFields.length }} 项</text>
          </view>
          <view class="field-list">
            <view v-for="field in visibleFields" :key="field.key" class="field-row">
              <text class="field-label">{{ field.label }}</text>
              <text class="field-value" :class="{ muted: !hasValue(record[field.key]) }">{{ displayValue(field) }}</text>
            </view>
          </view>
        </view>

        <view class="section-card material-card">
          <view class="section-head">
            <view>
              <text class="section-kicker">FILES & MATERIALS</text>
              <text class="section-title">相关资料</text>
            </view>
            <view class="add-more pressable" @tap="chooseMaterial"><Plus :size="14" /><text>添加</text></view>
          </view>

          <view v-if="materials.length" class="material-list">
            <MaterialRow v-for="item in materials" :key="item.material_id" :material="item" compact @open="openMaterialPage" />
          </view>
          <view v-else class="material-empty pressable" @tap="chooseMaterial">
            <view class="material-empty-icon"><FilePlus2 :size="22" /></view>
            <view class="material-empty-copy">
              <text class="material-empty-title">给这条记录补上现场材料</text>
              <text class="material-empty-note">照片、PDF、表格或其他文件都可以</text>
            </view>
            <ChevronRight :size="16" />
          </view>
          <view v-if="materialsError" class="material-error">
            <TriangleAlert :size="16" />
            <text>{{ materialsError }}</text>
          </view>
        </view>

        <view class="section-card link-card">
          <view class="section-head">
            <view>
              <text class="section-kicker">CONNECTED RECORDS</text>
              <text class="section-title">关联记录</text>
            </view>
            <text class="field-total">{{ linkedRecords.length }} 条</text>
          </view>

          <view v-if="linkedRecords.length" class="link-list">
            <view v-for="item in linkedRecords" :key="item.link_id" class="link-row pressable" @tap="openRelated(item)">
              <ModuleMark :module-key="item.module" size="sm" />
              <view class="link-copy">
                <view class="link-meta-line">
                  <text class="link-module">{{ item.module_label }}</text>
                  <text class="link-date">{{ item.business_date || "日期待补充" }}</text>
                </view>
                <text class="link-title">{{ item.title }}</text>
                <text class="link-note">{{ item.note || item.subtitle || item.relation_label }}</text>
              </view>
              <view v-if="item.can_remove" class="unlink-action pressable" @tap.stop="removeLink(item)">
                <LoaderCircle v-if="linkingId === item.link_id" :size="15" class="spin" />
                <Unlink v-else :size="15" />
              </view>
            </view>
          </view>
          <view v-else class="link-empty">
            <Link2 :size="18" />
            <text>还没有确认关联。下面有相似记录时，可以手动建立联系。</text>
          </view>

          <view v-if="suggestedRecords.length" class="suggestion-block">
            <view class="suggestion-head">
              <text>可能相关</text>
              <text>确认后再关联，不会自动合并</text>
            </view>
            <view v-for="item in suggestedRecords" :key="`${item.module}-${item.record_id}`" class="suggestion-row">
              <ModuleMark :module-key="item.module" size="sm" />
              <view class="suggestion-copy" @tap="openRelated(item)">
                <text class="suggestion-title">{{ item.title }}</text>
                <text class="suggestion-reason">{{ item.reason }}</text>
              </view>
              <button class="link-button pressable" :disabled="linkingId === item.record_id" @tap.stop="addLink(item)">
                <LoaderCircle v-if="linkingId === item.record_id" :size="13" class="spin" />
                <text v-else>关联</text>
              </button>
            </view>
          </view>

          <view v-if="linkError" class="material-error">
            <TriangleAlert :size="16" />
            <text>{{ linkError }}</text>
          </view>
        </view>

        <view v-if="attachmentList.length" class="section-card legacy-card">
          <view class="section-head">
            <view>
              <text class="section-kicker">LEGACY FILES</text>
              <text class="section-title">早期附件</text>
            </view>
            <text class="field-total">{{ attachmentList.length }} 份</text>
          </view>
          <view v-for="file in attachmentList" :key="file.attach_id" class="legacy-row pressable" @tap="openAttachment(file)">
            <view class="legacy-icon"><FileText :size="17" /></view>
            <view class="legacy-copy">
              <text class="legacy-name">{{ file.file_name }}</text>
              <text class="legacy-meta">{{ formatFileSize(file.file_size) }} · {{ formatDate(file.upload_time) }}</text>
            </view>
            <ExternalLink :size="15" class="legacy-arrow" />
          </view>
        </view>

        <view v-if="canShowShare" class="section-card share-card">
          <view class="share-copy">
            <view class="share-icon"><UsersRound :size="19" /></view>
            <view>
              <text class="share-title">团队共享</text>
              <text class="share-desc">{{ record.is_shared ? "团队可以查看这条工作记录" : "目前只有你能看到" }}</text>
            </view>
          </view>
          <switch :checked="Boolean(record.is_shared)" color="#0b7565" :disabled="!record.can_edit" @change="toggleShared" />
        </view>

        <view v-if="record.can_edit" class="record-actions">
          <button class="secondary-action pressable" @tap="editRecord"><Pencil :size="16" /><text>编辑记录</text></button>
          <button class="delete-action pressable" @tap="deleteRecord"><Trash2 :size="16" /><text>删除</text></button>
        </view>
        <view class="page-space"></view>
      </view>

      <StatePanel
        v-else-if="loading"
        state="loading"
        title="正在打开这条记录"
        description="记录字段和相关资料正在同步。"
      />
      <StatePanel
        v-else
        state="error"
        title="这条记录暂时打不开"
        :description="loadError || '记录可能已经删除，或者当前设备没有访问权限。'"
        action-text="重新加载"
        secondary-text="返回历史"
        @action="loadDetail"
        @secondary="goHistory"
      />
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad, onShow } from "@dcloudio/uni-app";
import {
  ChevronRight,
  ExternalLink,
  FilePlus2,
  FileText,
  Link2,
  LoaderCircle,
  Paperclip,
  Pencil,
  Plus,
  Unlink,
  Trash2,
  TriangleAlert,
  UsersRound,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import ModuleMark from "../../components/ModuleMark.vue";
import MaterialRow from "../../components/MaterialRow.vue";
import StatePanel from "../../components/StatePanel.vue";
import StatusNotice from "../../components/StatusNotice.vue";
import { modules, recordDate, recordTitle } from "../../data/modules";
import { request } from "../../services/api";
import { getCachedRecords } from "../../services/localDb";
import { chooseFiles, chooseImages, listMaterials, uploadMaterial } from "../../services/material";
import { getSession } from "../../services/session";
import {
  createRecordLink,
  deleteRecordLink,
  getRecordContext,
} from "../../services/workspace";

const moduleKey = ref("sale");
const recordId = ref("");
const record = ref(null);
const materials = ref([]);
const attachmentList = ref([]);
const linkedRecords = ref([]);
const suggestedRecords = ref([]);
const loading = ref(true);
const linkingId = ref("");
const linkError = ref("");
const uploading = ref(false);
const loadError = ref("");
const cacheNotice = ref("");
const actionError = ref("");
const materialsError = ref("");
const config = computed(() => modules[moduleKey.value]);
const statusMap = { 0: "未做", 1: "正在做", 2: "已做好", 3: "计划搁置" };

const title = computed(() => (record.value ? recordTitle(moduleKey.value, record.value) : ""));
const businessDate = computed(() => (record.value ? recordDate(moduleKey.value, record.value) : ""));
const subtitle = computed(() => {
  if (!record.value) return "";
  if (moduleKey.value === "sale") return record.value.deal_status;
  if (moduleKey.value === "lease") return record.value.lease_type;
  if (moduleKey.value === "work") return record.value.record_type;
  return record.value.inspiration_type;
});
const visibleFields = computed(() => {
  if (!record.value) return [];
  return config.value.fields.filter((field) => {
    if (field.adminOnly && getSession()?.role_level !== 1) return false;
    if (field.key === "commission_remark" && !record.value[field.key]) return false;
    return field.core || hasValue(record.value[field.key]);
  });
});
const canShowShare = computed(() => moduleKey.value === "work" && record.value?.record_type !== "每日复盘");

function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function displayValue(field) {
  const value = record.value?.[field.key];
  if (!hasValue(value)) return "未填写";
  if (field.key === "is_shared") return Number(value) ? "团队共享" : "仅本人可见";
  if (field.key === "ext_field_5") return statusMap[Number(value)] || "未做";
  if (field.type === "switch") return Number(value) ? "是" : "否";
  if (field.type === "datetime") return String(value).replace("T", " ").slice(0, 16);
  if (field.type === "date") return String(value).slice(0, 10);
  return `${value}${field.unit ? ` ${field.unit}` : ""}`;
}

function formatFileSize(bytes) {
  const value = Number(bytes || 0);
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value) {
  return String(value || "").replace("T", " ").slice(0, 16);
}

async function loadDetail() {
  loading.value = true;
  loadError.value = "";
  cacheNotice.value = "";
  try {
    const context = await getRecordContext(moduleKey.value, recordId.value);
    record.value = context.record;
    materials.value = context.materials?.items || [];
    attachmentList.value = context.attachments?.items || [];
    linkedRecords.value = context.links?.items || [];
    suggestedRecords.value = context.suggestions?.items || [];
    materialsError.value = "";
    linkError.value = "";
  } catch (error) {
    record.value = (await getCachedRecords(moduleKey.value)).find((item) => item.record_id === recordId.value) || null;
    if (record.value) cacheNotice.value = `${error.message || "服务暂时不可用"} 当前展示最近一次保存在本机的内容。`;
    else {
      try {
        record.value = await request(`/${config.value.endpoint}/${recordId.value}`);
      } catch (detailError) {
        loadError.value = detailError.message || error.message || "记录加载失败，请检查网络和资料库服务。";
      }
    }
    if (record.value) await Promise.allSettled([loadMaterials(), loadLegacyAttachments()]);
  }
  loading.value = false;
}

async function loadMaterials() {
  try {
    const response = await listMaterials({ module: moduleKey.value, recordId: recordId.value, pageSize: 100 });
    materials.value = response.items || [];
    materialsError.value = "";
  } catch (error) {
    materials.value = [];
    materialsError.value = error.message || "相关资料暂时没有加载出来。";
  }
}

async function loadLegacyAttachments() {
  try {
    const response = await request(`/attachments?biz_type=${moduleKey.value}&biz_id=${recordId.value}`);
    attachmentList.value = response.items || [];
  } catch (error) {
    attachmentList.value = [];
  }
}

async function refreshRelations() {
  const context = await getRecordContext(moduleKey.value, recordId.value);
  linkedRecords.value = context.links?.items || [];
  suggestedRecords.value = context.suggestions?.items || [];
}

function openRelated(item) {
  if (!item?.module || !item?.record_id) return;
  uni.navigateTo({ url: `/pages/detail/index?module=${item.module}&id=${item.record_id}` });
}

async function addLink(item) {
  if (linkingId.value) return;
  linkingId.value = item.record_id;
  linkError.value = "";
  try {
    await createRecordLink({
      sourceModule: moduleKey.value,
      sourceRecordId: recordId.value,
      targetModule: item.module,
      targetRecordId: item.record_id,
      relationType: item.relation_type || "related",
    });
    await refreshRelations();
    uni.showToast({ title: "已建立关联", icon: "success" });
  } catch (error) {
    linkError.value = error.message || "关联没有建立成功，请稍后重试。";
  } finally {
    linkingId.value = "";
  }
}

function removeLink(item) {
  uni.showModal({
    title: "取消关联",
    content: "只取消两条记录之间的联系，不会删除任何记录或资料。",
    confirmColor: "#b64c46",
    success: async (result) => {
      if (!result.confirm) return;
      linkingId.value = item.link_id;
      linkError.value = "";
      try {
        await deleteRecordLink(item.link_id);
        await refreshRelations();
        uni.showToast({ title: "已取消关联", icon: "success" });
      } catch (error) {
        linkError.value = error.message || "取消关联失败，请稍后重试。";
      } finally {
        linkingId.value = "";
      }
    },
  });
}

function editRecord() {
  uni.navigateTo({ url: `/pages/entry/index?module=${moduleKey.value}&id=${recordId.value}` });
}

function openMaterialPage(item) {
  uni.navigateTo({ url: `/pages/material/index?id=${item.material_id}` });
}

function goHistory() {
  uni.reLaunch({ url: `/pages/history/index?module=${moduleKey.value}` });
}

async function chooseMaterial() {
  if (uploading.value) return;
  uni.showActionSheet({
    itemList: ["拍照或从相册选择", "导入任意格式文件"],
    success: async (result) => {
      try {
        actionError.value = "";
        const files = result.tapIndex === 0
          ? await chooseImages({ count: 9, sourceType: ["album", "camera"] })
          : await chooseFiles({ count: 9 });
        if (!files.length) return;
        uploading.value = true;
        for (const file of files) {
          await uploadMaterial(file, {
            module: moduleKey.value,
            recordId: recordId.value,
            title: file.name.replace(/\.[^.]+$/, ""),
          });
        }
        uni.showToast({ title: `已补充 ${files.length} 份资料`, icon: "success" });
        await loadMaterials();
      } catch (error) {
        actionError.value = error.message || error.errMsg || "资料上传失败，请稍后重试。";
      } finally {
        uploading.value = false;
      }
    },
  });
}

function openAttachment(file) {
  if (file.file_type === "image") {
    uni.previewImage({ urls: [file.file_url], current: file.file_url });
    return;
  }
  // #ifdef H5
  window.open(file.file_url, "_blank", "noopener,noreferrer");
  return;
  // #endif
  uni.showLoading({ title: "正在打开" });
  uni.downloadFile({
    url: file.file_url,
    success: (result) => {
      if (result.statusCode === 200) uni.openDocument({ filePath: result.tempFilePath, showMenu: true });
      else uni.showToast({ title: "附件下载失败", icon: "none" });
    },
    fail: () => uni.showToast({ title: "附件下载失败", icon: "none" }),
    complete: () => uni.hideLoading(),
  });
}

async function toggleShared(event) {
  if (!record.value?.can_edit) return;
  const next = event.detail.value ? 1 : 0;
  actionError.value = "";
  try {
    record.value = await request(`/work-logs/${recordId.value}`, { method: "PATCH", data: { is_shared: next } });
    uni.showToast({ title: next ? "已设为团队共享" : "已设为仅本人可见", icon: "success" });
  } catch (error) {
    actionError.value = error.message || "共享设置没有保存成功，请稍后重试。";
  }
}

function deleteRecord() {
  if (!record.value?.can_edit) return;
  uni.showModal({
    title: "删除记录",
    content: "记录会进入回收站并保留 7 天。",
    confirmColor: "#b64c46",
    success: async (result) => {
      if (!result.confirm) return;
      try {
        await request(`/${config.value.endpoint}/${recordId.value}`, { method: "DELETE" });
        uni.showToast({ title: "已移入回收站", icon: "success" });
        setTimeout(() => uni.navigateBack(), 450);
      } catch (error) {
        actionError.value = error.message || "删除失败，请稍后重试。";
      }
    },
  });
}

onLoad((options) => {
  if (modules[options?.module]) moduleKey.value = options.module;
  recordId.value = options?.id || "";
  loadDetail();
});

onShow(() => {
  if (recordId.value && record.value) {
    loadMaterials();
    refreshRelations().catch(() => {});
  }
});
</script>

<style scoped>
.detail-page {
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
.detail-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.detail-content {
  padding: 4px 16px 0;
}
.record-hero {
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.tone-sale .record-hero {
  border-color: #ecd2c9;
  background: #fffaf8;
}
.tone-lease .record-hero {
  border-color: #cbe2dc;
  background: #f7fffc;
}
.tone-work .record-hero {
  border-color: #d1dceb;
  background: #f8faff;
}
.tone-inspiration .record-hero {
  border-color: #e9d4db;
  background: #fff9fb;
}
.hero-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.hero-meta {
  text-align: right;
}
.hero-kicker {
  display: block;
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.09em;
}
.hero-date {
  display: block;
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 10px;
}
.record-title {
  display: block;
  margin-top: 17px;
  color: var(--ink);
  font-size: 22px;
  font-weight: 760;
  line-height: 30px;
  word-break: break-word;
}
.hero-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 10px;
}
.hero-badge {
  padding: 3px 7px;
  border: 1px solid rgba(28, 40, 37, 0.08);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.65);
  color: var(--text-secondary);
  font-size: 8px;
  font-weight: 600;
}
.hero-actions {
  display: flex;
  gap: 8px;
  margin-top: 17px;
}
.edit-button,
.add-file-button {
  height: 41px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 650;
}
.edit-button {
  flex: 1.1;
  background: var(--ink);
  color: #ffffff;
}
.add-file-button {
  flex: 1;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-primary);
}
.section-card {
  margin-top: 12px;
  padding: 15px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.section-head {
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
  letter-spacing: 0.09em;
}
.section-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 700;
}
.field-total {
  color: var(--text-muted);
  font-size: 9px;
}
.field-list {
  margin-top: 9px;
}
.field-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
}
.field-label {
  width: 100px;
  flex: none;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 18px;
}
.field-value {
  flex: 1;
  color: var(--text-primary);
  font-size: 11px;
  line-height: 18px;
  text-align: right;
  white-space: pre-wrap;
  word-break: break-word;
}
.field-value.muted {
  color: var(--text-muted);
}
.material-list {
  margin-top: 7px;
}
.add-more {
  min-height: 29px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 0 8px;
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--accent);
  font-size: 9px;
}
.material-empty {
  min-height: 76px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  padding: 11px;
  border: 1px dashed #cfdcd7;
  border-radius: 8px;
  background: #fafcfb;
}
.material-empty-icon {
  width: 39px;
  height: 39px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--accent);
}
.material-empty-copy {
  flex: 1;
  min-width: 0;
}
.material-empty-title {
  display: block;
  color: var(--text-primary);
  font-size: 10px;
  font-weight: 650;
}
.material-empty-note {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 8px;
}
.legacy-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
}
.legacy-card .section-head + .legacy-row {
  margin-top: 9px;
}
.legacy-icon {
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: var(--surface-soft);
  color: var(--accent);
}
.legacy-copy {
  flex: 1;
  min-width: 0;
}
.legacy-name {
  display: block;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 10px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.legacy-meta {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 8px;
}
.legacy-arrow {
  flex: none;
  color: var(--text-muted);
}
.share-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.share-copy {
  display: flex;
  align-items: center;
  gap: 10px;
}
.share-icon {
  width: 38px;
  height: 38px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--work-soft);
  color: var(--work);
}
.share-title {
  display: block;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 650;
}
.share-desc {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 8px;
}
.record-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
.secondary-action,
.delete-action {
  height: 43px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 7px;
  font-size: 10px;
  font-weight: 650;
}
.secondary-action {
  flex: 1;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-primary);
}
.delete-action {
  width: 100px;
  border: 1px solid #ebd5d1;
  background: #fff8f6;
  color: var(--danger);
}
.loading-page {
  min-height: 75vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--text-muted);
  font-size: 10px;
}
.page-space {
  height: calc(26px + env(safe-area-inset-bottom));
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.record-hero,
.section-card,
.image-preview {
  border-radius: 8px;
}
.hero-kicker,
.section-kicker {
  font-size: 10px;
  letter-spacing: 0;
}
.hero-date,
.field-total,
.material-empty-note,
.legacy-meta,
.share-desc {
  font-size: 11px;
}
.hero-badge {
  font-size: 11px;
  line-height: 17px;
}
.edit-button,
.add-file-button,
.secondary-action,
.delete-action {
  font-size: 13px;
}
.section-title {
  font-size: 16px;
}
.field-label,
.add-more {
  font-size: 12px;
}
.field-value {
  font-size: 14px;
  line-height: 21px;
}
.field-label {
  line-height: 21px;
}
.material-empty-title,
.legacy-name,
.share-title {
  font-size: 13px;
}
.material-error {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 10px;
  padding: 9px 10px;
  border-radius: 7px;
  background: var(--warning-bg);
  color: #8b5128;
  font-size: 12px;
  line-height: 18px;
}
.material-error svg {
  flex: none;
  margin-top: 1px;
}
.link-list {
  margin-top: 8px;
}
.link-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 0;
  border-top: 1px solid var(--border);
}
.link-copy {
  flex: 1;
  min-width: 0;
}
.link-meta-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.link-module {
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
}
.link-date {
  color: var(--text-muted);
  font-size: 10px;
}
.link-title {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.link-note {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 17px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.unlink-action {
  width: 32px;
  height: 32px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 7px;
  color: var(--text-muted);
}
.link-empty {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 10px;
  padding: 11px;
  border: 1px dashed #cfdcd7;
  border-radius: 8px;
  background: #fafcfb;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 17px;
}
.suggestion-block {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.suggestion-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 3px;
}
.suggestion-head text:first-child {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
}
.suggestion-head text:last-child {
  color: var(--text-muted);
  font-size: 10px;
}
.suggestion-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding-top: 9px;
}
.suggestion-copy {
  flex: 1;
  min-width: 0;
}
.suggestion-title {
  display: block;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.suggestion-reason {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
}
.link-button {
  width: 53px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: var(--surface);
  color: var(--accent);
  font-size: 11px;
}
.link-button[disabled] {
  opacity: 0.55;
}
.loading-page {
  display: none;
}
</style>
