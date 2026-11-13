<template>
  <view v-if="visible" class="modal-mask" @tap="emit('close')">
    <view class="dialog" @tap.stop>
      <view class="dialog-header">
        <view>
          <text class="title">每日计划确认</text>
          <text class="date">{{ recordDate }}</text>
        </view>
        <text class="close" @tap="emit('close')">关闭</text>
      </view>

      <scroll-view class="plan-list" scroll-y>
        <view v-if="!plans.length" class="empty">今天没有待办计划</view>
        <view v-for="plan in plans" :key="plan.record_id" class="plan-row">
          <view class="plan-main">
            <text class="plan-time">{{ plan.ext_field_4 || "全天" }}</text>
            <text class="plan-content">{{ plan.content }}</text>
          </view>
          <view class="status-row">
            <button
              v-for="item in statuses"
              :key="item.value"
              class="status-button"
              :class="{ selected: Number(localStatuses[plan.record_id] ?? plan.ext_field_5) === item.value }"
              @tap="selectStatus(plan, item)"
            >
              {{ item.label }}
            </button>
          </view>
          <view v-if="editingId === plan.record_id" class="note-box">
            <textarea
              v-model="note"
              class="note-input"
              :placeholder="statusPlaceholder"
              maxlength="500"
            />
            <view class="note-actions">
              <button class="note-cancel" @tap="cancelNote">取消</button>
              <button class="note-save" @tap="saveNote(plan)">保存状态</button>
            </view>
          </view>
          <text v-if="plan.ext_field_1" class="history-note">{{ plan.ext_field_1 }}</text>
        </view>
      </scroll-view>

      <view class="insight-block">
        <text class="insight-label">今日整体心得</text>
        <textarea v-model="insight" class="insight-input" placeholder="可填写今日整体复盘" maxlength="2000" />
      </view>

      <button class="archive-button" :disabled="saving || !!editingId" @tap="archive">
        {{ saving ? "归档中..." : "确认并归档" }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  visible: Boolean,
  plans: { type: Array, default: () => [] },
  recordDate: { type: String, default: "" },
  saving: Boolean,
});
const emit = defineEmits(["close", "archive", "update-plan"]);

const statuses = [
  { value: 0, label: "未做" },
  { value: 1, label: "正在做" },
  { value: 2, label: "已做好" },
  { value: 3, label: "计划搁置" },
];
const localStatuses = ref({});
const editingId = ref("");
const editingStatus = ref(0);
const note = ref("");
const insight = ref("");

const statusPlaceholder = computed(() => {
  if (editingStatus.value === 1) return "填写当前进展";
  if (editingStatus.value === 2) return "填写完成情况与心得";
  if (editingStatus.value === 3) return "填写搁置原因";
  return "可补充说明";
});

function selectStatus(plan, item) {
  localStatuses.value[plan.record_id] = item.value;
  if (item.value === 0) {
    emit("update-plan", { plan, status: 0, note: "" });
    return;
  }
  editingId.value = plan.record_id;
  editingStatus.value = item.value;
  note.value = "";
}

function cancelNote() {
  editingId.value = "";
  note.value = "";
}

function saveNote(plan) {
  if (!note.value.trim()) {
    uni.showToast({ title: statusPlaceholder.value, icon: "none" });
    return;
  }
  emit("update-plan", { plan, status: editingStatus.value, note: note.value.trim() });
  cancelNote();
}

function archive() {
  emit("archive", insight.value.trim());
  insight.value = "";
}
</script>

<style scoped>
.modal-mask {
  position: fixed;
  z-index: 999;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: env(safe-area-inset-top) 0 env(safe-area-inset-bottom);
  background: rgba(0, 0, 0, 0.32);
}
.dialog {
  width: 80%;
  max-height: 82vh;
  padding: 16px;
  border-radius: 8px;
  background: var(--surface);
  display: flex;
  flex-direction: column;
}
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}
.title,
.date {
  display: block;
}
.title {
  font-size: 17px;
  font-weight: 600;
}
.date {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}
.close {
  color: var(--text-secondary);
  font-size: 13px;
}
.plan-list {
  min-height: 120px;
  max-height: 34vh;
}
.plan-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.plan-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.plan-time {
  width: 42px;
  flex: none;
  color: var(--text-secondary);
  font-size: 12px;
}
.plan-content {
  color: var(--text-primary);
  font-size: 13px;
  line-height: 20px;
}
.status-row {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}
.status-button {
  height: 28px;
  padding: 0 6px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 26px;
}
.status-button.selected {
  border-color: var(--accent);
  background: var(--accent);
  color: #ffffff;
}
.note-box {
  margin-top: 8px;
  padding: 8px;
  background: var(--page-bg);
}
.note-input {
  width: 100%;
  height: 58px;
  color: var(--text-primary);
  font-size: 12px;
  line-height: 18px;
}
.note-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 6px;
}
.note-cancel,
.note-save {
  height: 28px;
  padding: 0 10px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 28px;
}
.note-cancel {
  background: var(--surface);
  color: var(--text-secondary);
}
.note-save {
  background: var(--accent);
  color: #ffffff;
}
.history-note {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 11px;
  white-space: pre-wrap;
}
.empty {
  padding: 24px 0;
  color: var(--text-muted);
  text-align: center;
}
.insight-block {
  margin-top: 12px;
}
.insight-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
}
.insight-input {
  width: 100%;
  height: 68px;
  padding: 8px;
  border-radius: 4px;
  background: var(--page-bg);
  color: var(--text-primary);
  font-size: 12px;
  line-height: 18px;
}
.archive-button {
  height: 42px;
  margin-top: 12px;
  border-radius: 4px;
  background: var(--accent);
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  line-height: 42px;
}
.archive-button[disabled] {
  opacity: 0.5;
}
</style>
