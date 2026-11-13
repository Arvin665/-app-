<template>
  <el-drawer
    :model-value="modelValue"
    :title="drawerTitle"
    size="440px"
    direction="rtl"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="record" class="drawer-content">
      <div class="drawer-actions">
        <el-button v-if="!editing && record.can_edit" :icon="Edit" @click="editing = true">编辑</el-button>
        <template v-else>
          <el-button @click="cancelEdit">取消</el-button>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </template>
        <el-button v-if="record.can_edit" :icon="Delete" type="danger" plain @click="remove">删除</el-button>
      </div>

      <div v-if="!editing" class="view-panel">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="记录ID">{{ record.record_id }}</el-descriptions-item>
          <el-descriptions-item v-for="field in visibleFields" :key="field.key" :label="field.label">
            <span :class="{ 'empty-value': !hasValue(form[field.key]) }">
              {{ formatValue(field) || "未填写" }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(record.update_time) }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <el-form v-else label-position="top" class="edit-form">
        <el-form-item v-for="field in visibleFields" :key="field.key" :label="field.label" :required="field.required">
          <el-input
            v-if="field.type === 'text'"
            v-model="form[field.key]"
            :placeholder="`请输入${field.label}`"
          />
          <el-input-number
            v-else-if="field.type === 'number'"
            v-model="form[field.key]"
            :controls="false"
            :precision="2"
            :placeholder="field.unit ? `单位：${field.unit}` : ''"
          />
          <el-date-picker
            v-else-if="field.type === 'date'"
            v-model="form[field.key]"
            type="date"
            value-format="YYYY-MM-DD"
          />
          <el-time-picker
            v-else-if="field.type === 'time'"
            v-model="form[field.key]"
            value-format="HH:mm"
            format="HH:mm"
            placeholder="全天计划可留空"
          />
          <el-date-picker
            v-else-if="field.type === 'datetime'"
            v-model="form[field.key]"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
          <el-select v-else-if="field.type === 'select'" v-model="form[field.key]" clearable>
            <el-option
              v-for="(option, index) in field.options"
              :key="option"
              :label="option"
              :value="field.optionValues ? field.optionValues[index] : option"
            />
          </el-select>
          <el-switch
            v-else-if="field.type === 'switch'"
            v-model="form[field.key]"
            :active-value="1"
            :inactive-value="0"
          />
          <el-input
            v-else
            v-model="form[field.key]"
            type="textarea"
            :rows="field.readonly ? 4 : 3"
            :readonly="field.readonly"
          />
          <span v-if="field.unit" class="field-unit">{{ field.unit }}</span>
        </el-form-item>
      </el-form>

      <div class="attachment-section">
        <div class="section-head">
          <span>附件</span>
          <span class="attachment-count">{{ attachments.length }}</span>
        </div>
        <div v-if="!attachments.length" class="attachment-empty">暂无附件</div>
        <div v-for="file in attachments" :key="file.attach_id" class="attachment-row">
          <el-icon><Paperclip /></el-icon>
          <div class="attachment-main">
            <a :href="file.file_url" target="_blank" rel="noreferrer">{{ file.file_name }}</a>
            <span>{{ formatSize(file.file_size) }} · {{ formatDateTime(file.upload_time) }}</span>
          </div>
          <a :href="file.file_url" target="_blank" rel="noreferrer" class="preview-link">预览</a>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Edit, Paperclip } from "@element-plus/icons-vue";
import { api, isNetworkError } from "../services/api";
import { saveRecordOffline } from "../services/offline";
import { displayTitle, modules } from "../data/modules";

const props = defineProps({
  modelValue: Boolean,
  module: { type: String, required: true },
  record: { type: Object, default: null },
  startEditing: Boolean,
  roleLevel: { type: Number, default: 2 },
});
const emit = defineEmits(["update:modelValue", "saved", "deleted"]);
const editing = ref(false);
const saving = ref(false);
const attachments = ref([]);
const form = reactive({});
const config = computed(() => modules[props.module]);
const drawerTitle = computed(() => (props.record ? displayTitle(props.module, props.record) : "记录详情"));
const visibleFields = computed(() =>
  config.value.fields.filter((field) => !(field.adminOnly && Number(props.roleLevel) !== 1)),
);

function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function fillForm(record = {}) {
  Object.keys(form).forEach((key) => delete form[key]);
  const normalized = { ...record };
  config.value.fields.forEach((field) => {
    const value = normalized[field.key];
    if (field.type === "number" && value !== null && value !== undefined && value !== "") {
      const numeric = Number(value);
      normalized[field.key] = Number.isFinite(numeric) ? numeric : null;
    }
  });
  Object.assign(form, normalized);
}

function formatValue(field) {
  const value = form[field.key];
  if (!hasValue(value)) return "";
  if (field.key === "is_shared") return Number(value) ? "团队共享" : "仅本人可见";
  if (field.key === "ext_field_5") return ["未做", "正在做", "已做好", "计划搁置"][Number(value)] || "未做";
  if (field.type === "switch") return Number(value) ? "是" : "否";
  return `${value}${field.unit ? ` ${field.unit}` : ""}`;
}

function formatDateTime(value) {
  return value ? String(value).replace("T", " ").slice(0, 16) : "";
}

function formatSize(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function loadAttachments() {
  attachments.value = [];
  if (!form.record_id) return;
  try {
    const result = await api(`/attachments?biz_type=${props.module}&biz_id=${form.record_id}`);
    attachments.value = result.items || [];
  } catch (error) {
    console.warn("附件列表加载失败", error);
  }
}

watch(
  () => [props.modelValue, props.record?.record_id, props.startEditing],
  ([open, , startEditing]) => {
    if (!open || !props.record) return;
    fillForm(props.record);
    editing.value = Boolean(startEditing && props.record?.can_edit);
    loadAttachments();
  },
  { immediate: true },
);
watch(
  () => props.startEditing,
  (start) => {
    if (props.modelValue && props.record?.can_edit) editing.value = Boolean(start);
  },
);

function normalizePayload() {
  const payload = {};
  visibleFields.value.forEach((field) => {
    if (field.readonly) return;
    const value = form[field.key];
    if (value === "" || value === undefined) {
      payload[field.key] = field.required ? value : null;
    } else {
      payload[field.key] = value;
    }
  });
  return payload;
}

function cancelEdit() {
  fillForm(props.record);
  editing.value = false;
}

async function save() {
  const missing = visibleFields.value.find((field) => field.required && !hasValue(form[field.key]));
  if (missing) {
    ElMessage.warning(`请填写${missing.label}`);
    return;
  }
  saving.value = true;
  const payload = normalizePayload();
  try {
    let updated;
    let force = false;
    let duplicateConfirmed = false;
    while (!updated) {
      try {
        updated = await api(`/${config.value.endpoint}/${form.record_id}${force ? "?force=true" : ""}`, {
          method: "PATCH",
          data: payload,
        });
      } catch (error) {
        if (error.status === 409 && !duplicateConfirmed) {
          duplicateConfirmed = true;
          const confirmed = await ElMessageBox.confirm("发现相近记录，仍然保存本次修改？", "重复提示", {
            confirmButtonText: "仍然保存",
            cancelButtonText: "返回核对",
            type: "warning",
          }).then(() => true).catch(() => false);
          if (!confirmed) return;
          force = true;
          continue;
        }
        if (!isNetworkError(error)) throw error;
        updated = await saveRecordOffline(props.module, form.record_id, payload);
        ElMessage.warning("网络不可用，修改已保存在本地，联网后自动同步");
      }
    }
    if (updated !== undefined && !updated?.offline) ElMessage.success("记录已保存");
    fillForm(updated);
    editing.value = false;
    emit("saved", updated);
  } catch (error) {
    ElMessage.error(error.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function remove() {
  const confirmed = await ElMessageBox.confirm("记录将进入回收站并保留 7 天。", "删除记录", {
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    type: "warning",
  }).then(() => true).catch(() => false);
  if (!confirmed) return;
  try {
    await api(`/${config.value.endpoint}/${form.record_id}`, { method: "DELETE" });
    ElMessage.success("已移入回收站");
    emit("deleted", form.record_id);
    emit("update:modelValue", false);
  } catch (error) {
    ElMessage.error(error.message || "删除失败");
  }
}
</script>

<style scoped>
.drawer-content {
  min-height: 100%;
  padding: 14px 16px 24px;
}
.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-bottom: 14px;
}
.view-panel :deep(.el-descriptions__label) {
  width: 100px;
  color: #666666;
  font-weight: 400;
}
.view-panel :deep(.el-descriptions__content) {
  color: #333333;
  white-space: pre-wrap;
  word-break: break-word;
}
.empty-value {
  color: #999999;
}
.edit-form :deep(.el-input-number),
.edit-form :deep(.el-date-editor),
.edit-form :deep(.el-select) {
  width: 100%;
}
.field-unit {
  display: block;
  margin-top: 3px;
  color: #999999;
  font-size: 10px;
}
.attachment-section {
  margin-top: 18px;
  border-top: 1px solid #e5e6eb;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0 8px;
  font-size: 13px;
  font-weight: 600;
}
.attachment-count {
  color: #999999;
  font-size: 11px;
  font-weight: 400;
}
.attachment-empty {
  padding: 12px 0;
  color: #999999;
  font-size: 11px;
}
.attachment-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 0;
  border-top: 1px solid #f0f1f3;
}
.attachment-main {
  flex: 1;
  min-width: 0;
}
.attachment-main a {
  display: block;
  overflow: hidden;
  color: #333333;
  font-size: 12px;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attachment-main span {
  display: block;
  margin-top: 3px;
  color: #999999;
  font-size: 10px;
}
.preview-link {
  color: #165dff;
  font-size: 11px;
  text-decoration: none;
}
</style>
