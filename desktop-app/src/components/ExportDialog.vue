<template>
  <el-dialog
    :model-value="modelValue"
    title="Excel 导出"
    width="520px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-position="top">
      <el-form-item label="时间周期">
        <el-select v-model="periodType" clearable placeholder="全部时间">
          <el-option label="按日" value="day" />
          <el-option label="按周" value="week" />
          <el-option label="按月" value="month" />
          <el-option label="按季度" value="quarter" />
          <el-option label="按年度" value="year" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="periodType" label="周期值">
        <el-input v-model="periodValue" :placeholder="periodPlaceholder" />
      </el-form-item>
      <el-form-item label="起止日期（可选）">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          unlink-panels
        />
      </el-form-item>
      <el-form-item label="关键词（可选）">
        <el-input v-model="keyword" clearable placeholder="沿用当前搜索词" />
      </el-form-item>
    </el-form>
    <div class="export-note">
      导出字段与数据库母表完全对应；普通成员的佣金备注列自动置空，仅管理员可导出明文。
    </div>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="exporting" @click="runExport">导出 {{ modules[module].name }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { downloadFile } from "../services/api";
import { modules } from "../data/modules";
import { localDateString } from "../utils/date";

const props = defineProps({
  modelValue: Boolean,
  module: { type: String, required: true },
  defaultKeyword: { type: String, default: "" },
});
const emit = defineEmits(["update:modelValue"]);
const periodType = ref("");
const periodValue = ref("");
const dateRange = ref([]);
const keyword = ref("");
const exporting = ref(false);

const periodPlaceholder = computed(() => ({
  day: "如 2026-11-13",
  week: "如 2026-W46",
  month: "如 2026-11",
  quarter: "如 2026-Q4",
  year: "如 2026",
}[periodType.value] || ""));

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      periodType.value = "";
      periodValue.value = "";
      dateRange.value = [];
      keyword.value = props.defaultKeyword;
    }
  },
);

async function runExport() {
  if (periodType.value && !periodValue.value.trim()) {
    ElMessage.warning("请填写周期值");
    return;
  }
  exporting.value = true;
  try {
    const params = new URLSearchParams();
    if (periodType.value) params.set("period_type", periodType.value);
    if (periodValue.value) params.set("period_value", periodValue.value.trim());
    if (dateRange.value?.[0]) params.set("start_date", dateRange.value[0]);
    if (dateRange.value?.[1]) params.set("end_date", dateRange.value[1]);
    if (keyword.value.trim()) params.set("keyword", keyword.value.trim());
    await downloadFile(`/transfer/export/${props.module}?${params}`, `${modules[props.module].name}_${localDateString()}.xlsx`);
    ElMessage.success("Excel 已开始下载");
    emit("update:modelValue", false);
  } catch (error) {
    ElMessage.error(error.message || "导出失败");
  } finally {
    exporting.value = false;
  }
}
</script>

<style scoped>
.export-note {
  padding: 10px 12px;
  background: #fff7e6;
  color: #666666;
  font-size: 11px;
  line-height: 18px;
}
.el-select,
.el-date-editor {
  width: 100%;
}
</style>
