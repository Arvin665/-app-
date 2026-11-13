<template>
  <el-dialog
    :model-value="modelValue"
    title="Excel 导入"
    width="760px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
    @open="reset"
  >
    <div class="step-copy">1. 选择本模块导出的 .xlsx 母表；2. 预检重复行；3. 明确选择覆盖、跳过或另存。</div>
    <el-upload
      drag
      :auto-upload="false"
      :limit="1"
      accept=".xlsx"
      :on-change="onFileChange"
      :on-exceed="onExceed"
    >
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖入 Excel，或<em>点击选择文件</em></div>
      <template #tip><div class="el-upload__tip">仅支持 .xlsx，单文件不超过 50MB。</div></template>
    </el-upload>

    <div v-if="preview" class="preview-box">
      <div class="preview-summary">
        <span>数据行 <strong>{{ preview.total_rows }}</strong></span>
        <span>有效 <strong>{{ preview.valid_rows }}</strong></span>
        <span :class="{ warning: preview.duplicate_count }">重复 <strong>{{ preview.duplicate_count }}</strong></span>
        <span :class="{ danger: preview.error_count }">错误 <strong>{{ preview.error_count }}</strong></span>
      </div>
      <el-alert
        v-if="preview.duplicate_count"
        type="warning"
        :closable="false"
        title="发现重复数据，必须选择处理方式，系统不会静默覆盖。"
      />
      <el-table v-if="preview.duplicates.length" :data="preview.duplicates" max-height="160" size="small">
        <el-table-column prop="row" label="行号" width="70" />
        <el-table-column prop="summary" label="重复摘要" min-width="280" />
      </el-table>
      <el-table v-if="preview.errors.length" :data="preview.errors" max-height="140" size="small">
        <el-table-column prop="row" label="错误行" width="80" />
        <el-table-column prop="error" label="错误原因" min-width="420" />
      </el-table>
      <el-radio-group v-model="duplicateAction" class="action-group">
        <el-radio-button value="overwrite">覆盖已有记录</el-radio-button>
        <el-radio-button value="skip">跳过重复行</el-radio-button>
        <el-radio-button value="create_new">另存为新记录</el-radio-button>
      </el-radio-group>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button :loading="checking" :disabled="!file" @click="runPreview">预检</el-button>
      <el-button type="primary" :loading="importing" :disabled="!preview" @click="runImport">
        确认导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { UploadFilled } from "@element-plus/icons-vue";
import { uploadFile } from "../services/api";
import { modules } from "../data/modules";

const props = defineProps({
  modelValue: Boolean,
  module: { type: String, required: true },
});
const emit = defineEmits(["update:modelValue", "imported"]);
const file = ref(null);
const preview = ref(null);
const duplicateAction = ref("skip");
const checking = ref(false);
const importing = ref(false);

function onFileChange(uploadFileItem) {
  file.value = uploadFileItem.raw;
  preview.value = null;
}

function onExceed(files) {
  file.value = files[0];
  preview.value = null;
}

function reset() {
  file.value = null;
  preview.value = null;
  duplicateAction.value = "skip";
  checking.value = false;
  importing.value = false;
}

async function runPreview() {
  if (!file.value) return;
  checking.value = true;
  try {
    preview.value = await uploadFile(`/transfer/import/preview/${props.module}`, file.value);
    if (!preview.value.valid_rows) ElMessage.warning("没有可导入的有效数据，请检查表头与必填字段");
  } catch (error) {
    ElMessage.error(error.message || "Excel 预检失败");
  } finally {
    checking.value = false;
  }
}

async function runImport() {
  if (!file.value || !preview.value) return;
  importing.value = true;
  try {
    const result = await uploadFile(`/transfer/import/${props.module}`, file.value, {
      duplicate_action: duplicateAction.value,
    });
    ElMessage.success(`导入完成：新增 ${result.created}，覆盖 ${result.overwritten}，跳过 ${result.skipped}`);
    emit("imported", result);
    emit("update:modelValue", false);
  } catch (error) {
    ElMessage.error(error.message || "Excel 导入失败");
  } finally {
    importing.value = false;
  }
}
</script>

<style scoped>
.step-copy {
  margin-bottom: 12px;
  color: #666666;
  font-size: 12px;
  line-height: 20px;
}
.upload-icon {
  margin-bottom: 8px;
  color: #666666;
  font-size: 28px;
}
.preview-box {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid #e5e6eb;
  background: #f7f8fa;
}
.preview-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 10px;
  color: #666666;
  font-size: 12px;
}
.preview-summary strong {
  color: #333333;
  font-size: 15px;
}
.preview-summary .warning strong {
  color: #ff7d00;
}
.preview-summary .danger strong {
  color: #f53f3f;
}
.action-group {
  margin-top: 12px;
}
</style>
