<template>
  <el-dialog
    :model-value="modelValue"
    title="每日计划确认"
    width="720px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
    @open="loadPlans"
  >
    <div class="dialog-summary">
      <span>{{ recordDate }}</span>
      <span>共 {{ plans.length }} 项计划</span>
      <span v-if="locked" class="locked">已归档锁定</span>
    </div>

    <el-alert
      v-if="locked"
      type="info"
      :closable="false"
      title="当日计划已归档，状态不能再修改。"
      class="mb-16"
    />

    <div class="plan-list">
      <div v-if="!plans.length && !loading" class="empty-state">今天没有待办计划</div>
      <div v-for="plan in plans" :key="plan.record_id" class="plan-row">
        <div class="plan-main">
          <div class="plan-copy">
            <strong>{{ plan.ext_field_4 || "全天" }} · {{ plan.content }}</strong>
            <span>{{ plan.related_project || "未关联项目" }}</span>
          </div>
          <el-select
            :model-value="Number(plan.ext_field_5 ?? 0)"
            :disabled="locked || updatingId === plan.record_id"
            class="status-select"
            @change="changeStatus(plan, $event)"
          >
            <el-option v-for="status in statuses" :key="status.value" :label="status.label" :value="status.value" />
          </el-select>
        </div>
        <div v-if="plan.ext_field_1" class="plan-note">{{ plan.ext_field_1 }}</div>
      </div>
    </div>

    <div class="insight-block">
      <div class="insight-label">今日整体心得</div>
      <el-input v-model="insight" type="textarea" :rows="3" maxlength="2000" placeholder="可填写今日整体复盘" />
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">稍后确认</el-button>
      <el-button type="primary" :loading="archiving" :disabled="locked || !plans.length" @click="archive">
        确认并归档
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../services/api";

const props = defineProps({
  modelValue: Boolean,
  recordDate: { type: String, required: true },
});
const emit = defineEmits(["update:modelValue", "archived"]);
const plans = ref([]);
const locked = ref(false);
const loading = ref(false);
const archiving = ref(false);
const updatingId = ref("");
const insight = ref("");
const statuses = [
  { value: 0, label: "未做" },
  { value: 1, label: "正在做" },
  { value: 2, label: "已做好" },
  { value: 3, label: "计划搁置" },
];

function promptForStatus(status) {
  if (status === 1) return { label: "当前进展", placeholder: "填写正在做的事项和进展" };
  if (status === 2) return { label: "完成情况与心得", placeholder: "填写完成情况和复盘" };
  return { label: "搁置原因", placeholder: "填写计划搁置原因" };
}

async function loadPlans() {
  loading.value = true;
  try {
    const result = await api(`/work-logs/plans?record_date=${props.recordDate}`);
    plans.value = result.items || [];
    locked.value = Boolean(result.locked);
  } catch (error) {
    ElMessage.error(error.message || "计划加载失败");
  } finally {
    loading.value = false;
  }
}

async function changeStatus(plan, status) {
  let note = "";
  if (status !== 0) {
    const prompt = promptForStatus(status);
    try {
      const result = await ElMessageBox.prompt(prompt.placeholder, prompt.label, {
        confirmButtonText: "保存",
        cancelButtonText: "取消",
        inputValidator: (value) => Boolean(value?.trim()) || "此项不能为空",
      });
      note = result.value.trim();
    } catch (error) {
      await loadPlans();
      return;
    }
  }
  updatingId.value = plan.record_id;
  try {
    await api(`/work-logs/${plan.record_id}/status`, { method: "POST", data: { status, note } });
    ElMessage.success("计划状态已更新");
    await loadPlans();
  } catch (error) {
    ElMessage.error(error.message || "状态更新失败");
    await loadPlans();
  } finally {
    updatingId.value = "";
  }
}

async function archive() {
  archiving.value = true;
  try {
    await api("/work-logs/archive-daily", {
      method: "POST",
      data: { record_date: props.recordDate, insight: insight.value.trim() },
    });
    ElMessage.success("已归档为每日复盘");
    emit("archived");
    emit("update:modelValue", false);
  } catch (error) {
    ElMessage.error(error.message || "归档失败");
  } finally {
    archiving.value = false;
  }
}
</script>

<style scoped>
.dialog-summary {
  display: flex;
  gap: 18px;
  margin-bottom: 12px;
  color: #666666;
  font-size: 12px;
}
.locked {
  color: #ff7d00;
}
.plan-list {
  max-height: 340px;
  overflow: auto;
  border-top: 1px solid #e5e6eb;
}
.plan-row {
  padding: 12px 0;
  border-bottom: 1px solid #e5e6eb;
}
.plan-main {
  display: flex;
  align-items: center;
  gap: 16px;
}
.plan-copy {
  flex: 1;
  min-width: 0;
}
.plan-copy strong,
.plan-copy span {
  display: block;
}
.plan-copy strong {
  overflow: hidden;
  color: #333333;
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.plan-copy span {
  margin-top: 4px;
  color: #999999;
  font-size: 10px;
}
.status-select {
  width: 110px;
  flex: none;
}
.plan-note {
  margin-top: 8px;
  padding: 7px 8px;
  background: #f5f7fa;
  color: #666666;
  font-size: 11px;
  line-height: 18px;
  white-space: pre-wrap;
}
.insight-block {
  margin-top: 16px;
}
.insight-label {
  margin-bottom: 7px;
  color: #333333;
  font-size: 12px;
  font-weight: 600;
}
</style>
