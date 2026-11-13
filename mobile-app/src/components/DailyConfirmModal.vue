<template>
  <view v-if="visible" class="modal-mask" @tap="close">
    <view class="daily-sheet" @tap.stop>
      <view class="sheet-handle"></view>
      <view class="sheet-header">
        <view>
          <text class="header-kicker">DAILY REVIEW</text>
          <text class="header-title">{{ locked ? "今天的节奏已收好" : "收好今天" }}</text>
          <text class="header-date">{{ recordDate }}</text>
        </view>
        <view class="close-button pressable" @tap="close"><X :size="18" /></view>
      </view>

      <view class="progress-strip">
        <view>
          <text class="progress-number">{{ completedCount }}<text class="progress-unit"> / {{ plans.length }}</text></text>
          <text class="progress-label">今日已完成</text>
        </view>
        <view class="progress-track"><view class="progress-fill" :style="{ width: `${progressPercent}%` }"></view></view>
        <text class="progress-percent">{{ progressPercent }}%</text>
      </view>

      <scroll-view class="plan-list" scroll-y>
        <view v-if="!plans.length" class="empty">今天没有待办计划</view>
        <view v-for="plan in plans" :key="plan.record_id" class="plan-row">
          <view class="plan-head">
            <text class="plan-time">{{ plan.ext_field_4 || "全天" }}</text>
            <view class="plan-copy">
              <text class="plan-content">{{ plan.content || "未填写计划内容" }}</text>
              <text v-if="plan.related_project" class="plan-project">{{ plan.related_project }}</text>
            </view>
            <text class="plan-state">{{ statusMap[Number(localStatuses[plan.record_id] ?? plan.ext_field_5 ?? 0)] }}</text>
          </view>

          <view v-if="!locked" class="status-row">
            <view
              v-for="item in statuses"
              :key="item.value"
              class="status-button pressable"
              :class="{ selected: Number(localStatuses[plan.record_id] ?? plan.ext_field_5 ?? 0) === item.value }"
              @tap="selectStatus(plan, item)"
            >
              {{ item.short }}
            </view>
          </view>

          <view v-if="editingId === plan.record_id" class="note-box">
            <textarea v-model="note" class="note-input" :placeholder="statusPlaceholder" maxlength="500" auto-height />
            <text v-if="voiceKind === 'note'" class="voice-live">{{ voiceInterim || "正在听，请说这一步的情况..." }}</text>
            <view class="note-actions">
              <view class="note-voice pressable" :class="{ recording: voiceKind === 'note' }" @tap="toggleVoice('note')">
                <Square v-if="voiceKind === 'note'" :size="13" fill="currentColor" />
                <Mic v-else :size="15" />
                <text>{{ voiceKind === "note" ? "停止" : "说进展" }}</text>
              </view>
              <view class="note-buttons">
                <button class="note-cancel" @tap="cancelNote">取消</button>
                <button class="note-save" @tap="saveNote(plan)">保存</button>
              </view>
            </view>
          </view>

          <text v-if="plan.ext_field_1 && editingId !== plan.record_id" class="history-note">{{ latestNote(plan.ext_field_1) }}</text>
        </view>
      </scroll-view>

      <view class="insight-block">
        <view class="insight-head">
          <view>
            <text class="insight-kicker">TODAY'S NOTE</text>
            <text class="insight-label">今天整体留下了什么</text>
          </view>
          <view v-if="!locked" class="insight-mic pressable" :class="{ recording: voiceKind === 'insight' }" @tap="toggleVoice('insight')">
            <Square v-if="voiceKind === 'insight'" :size="13" fill="currentColor" />
            <Mic v-else :size="15" />
          </view>
        </view>
        <textarea
          v-model="insight"
          class="insight-input"
          placeholder="说说今天的判断、收获，或明天要继续的事"
          maxlength="2000"
          auto-height
          :disabled="locked"
        />
        <text v-if="voiceKind === 'insight'" class="voice-live">{{ voiceInterim || "正在听今天的心得..." }}</text>
      </view>

      <view v-if="locked" class="locked-state">
        <view class="locked-icon"><Check :size="17" /></view>
        <text>这一天已经归档，内容会留在工作记录里。</text>
      </view>
      <button v-else class="archive-button pressable" :disabled="saving || !!editingId" @tap="archive">
        <Check v-if="!saving" :size="18" />
        <Clock3 v-else :size="18" />
        <text>{{ saving ? "正在归档..." : editingId ? "请先保存当前进展" : "确认并归档今天" }}</text>
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { Check, Clock3, Mic, Square, X } from "@lucide/vue";
import { dictationAvailable, startDictation } from "../services/voice";

const props = defineProps({
  visible: Boolean,
  plans: { type: Array, default: () => [] },
  recordDate: { type: String, default: "" },
  saving: Boolean,
  locked: Boolean,
});
const emit = defineEmits(["close", "archive", "update-plan"]);

const statuses = [
  { value: 0, short: "未做" },
  { value: 1, short: "进行中" },
  { value: 2, short: "已做好" },
  { value: 3, short: "搁置" },
];
const statusMap = { 0: "未做", 1: "进行中", 2: "已做好", 3: "搁置" };
const localStatuses = ref({});
const editingId = ref("");
const editingStatus = ref(1);
const previousStatus = ref(0);
const previousEditingId = ref("");
const note = ref("");
const insight = ref("");
const voiceKind = ref("");
const voiceInterim = ref("");
let voiceSession = null;

const completedCount = computed(() => props.plans.filter((plan) => Number(plan.ext_field_5 ?? 0) === 2).length);
const progressPercent = computed(() => (props.plans.length ? Math.round((completedCount.value / props.plans.length) * 100) : 0));
const statusPlaceholder = computed(() => {
  if (editingStatus.value === 1) return "说说做到哪一步，下一步准备做什么";
  if (editingStatus.value === 2) return "说说完成情况，或这件事带来的判断";
  return "说说为什么暂缓，之后什么条件下继续";
});

function selectStatus(plan, item) {
  if (props.locked) return;
  stopVoice();
  previousStatus.value = Number(localStatuses.value[plan.record_id] ?? plan.ext_field_5 ?? 0);
  previousEditingId.value = plan.record_id;
  localStatuses.value[plan.record_id] = item.value;
  if (item.value === 0) {
    editingId.value = "";
    note.value = "";
    emit("update-plan", { plan, status: 0, note: "" });
    return;
  }
  editingId.value = plan.record_id;
  editingStatus.value = item.value;
  note.value = "";
}

function cancelNote() {
  if (previousEditingId.value && localStatuses.value[previousEditingId.value] !== undefined) {
    localStatuses.value[previousEditingId.value] = previousStatus.value;
  }
  editingId.value = "";
  note.value = "";
  stopVoice();
}

function saveNote(plan) {
  if (!note.value.trim()) {
    uni.showToast({ title: statusPlaceholder.value, icon: "none" });
    return;
  }
  emit("update-plan", { plan, status: editingStatus.value, note: note.value.trim() });
  editingId.value = "";
  note.value = "";
  stopVoice();
}

function latestNote(value) {
  const lines = String(value || "").split("\n").filter(Boolean);
  return lines[lines.length - 1] || "";
}

function appendText(current, text) {
  const value = String(current || "").trim();
  if (!value) return text;
  return `${value}${/[。！？!?]$/.test(value) ? "" : "。"}${text}`;
}

function toggleVoice(kind) {
  if (props.locked) return;
  if (voiceKind.value) {
    stopVoice();
    return;
  }
  if (!dictationAvailable()) {
    uni.showModal({
      title: "当前环境没有语音识别",
      content: "H5 建议使用 Edge/Chrome，App 内需要原生语音模块。你仍然可以输入文字。",
      showCancel: false,
    });
    return;
  }
  voiceKind.value = kind;
  voiceInterim.value = "";
  voiceSession = startDictation({
    continuous: false,
    onInterim: (text) => { voiceInterim.value = text; },
    onFinal: (text) => {
      if (!text.trim()) return;
      if (kind === "note") note.value = appendText(note.value, text.trim());
      if (kind === "insight") insight.value = appendText(insight.value, text.trim());
    },
    onError: (error) => uni.showToast({ title: error.message || "语音识别暂不可用", icon: "none" }),
    onEnd: () => {
      voiceKind.value = "";
      voiceInterim.value = "";
      voiceSession = null;
    },
  });
  if (!voiceSession) {
    voiceKind.value = "";
    voiceInterim.value = "";
  }
}

function stopVoice() {
  voiceSession?.stop?.();
  voiceSession = null;
  voiceKind.value = "";
  voiceInterim.value = "";
}

function close() {
  stopVoice();
  emit("close");
}

function archive() {
  if (props.locked || props.saving || editingId.value) return;
  emit("archive", insight.value.trim());
}

watch(() => props.visible, (visible) => {
  if (!visible) stopVoice();
});

onUnmounted(() => {
  voiceSession?.abort?.();
});
</script>

<style scoped>
.modal-mask {
  position: fixed;
  z-index: 999;
  inset: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-top: env(safe-area-inset-top);
  background: rgba(14, 25, 21, 0.44);
}
.daily-sheet {
  width: 100%;
  max-height: 91vh;
  display: flex;
  flex-direction: column;
  padding: 8px 16px calc(16px + env(safe-area-inset-bottom));
  border-radius: 15px 15px 0 0;
  background: var(--surface);
}
.sheet-handle {
  width: 36px;
  height: 4px;
  flex: none;
  margin: 0 auto 13px;
  border-radius: 2px;
  background: #d8e1dd;
}
.sheet-header {
  flex: none;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.header-kicker,
.insight-kicker {
  display: block;
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.11em;
}
.header-title {
  display: block;
  margin-top: 4px;
  color: var(--ink);
  font-size: 22px;
  font-weight: 750;
  line-height: 28px;
}
.header-date {
  display: block;
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: 10px;
}
.close-button {
  width: 35px;
  height: 35px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--soft);
  color: var(--text-secondary);
}
.progress-strip {
  flex: none;
  display: flex;
  align-items: center;
  gap: 11px;
  margin-top: 15px;
  padding: 11px 12px;
  border: 1px solid #d4e8e2;
  border-radius: 8px;
  background: #f3faf7;
}
.progress-number {
  display: block;
  color: var(--ink);
  font-size: 17px;
  font-weight: 750;
  line-height: 20px;
}
.progress-unit {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 500;
}
.progress-label {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 8px;
}
.progress-track {
  height: 5px;
  flex: 1;
  overflow: hidden;
  border-radius: 3px;
  background: #dfeae6;
}
.progress-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--accent);
}
.progress-percent {
  width: 32px;
  flex: none;
  color: var(--accent);
  font-size: 9px;
  font-weight: 700;
  text-align: right;
}
.plan-list {
  min-height: 100px;
  max-height: 33vh;
  margin-top: 12px;
  border-top: 1px solid var(--border);
}
.plan-row {
  padding: 11px 0;
  border-bottom: 1px solid var(--border);
}
.plan-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.plan-time {
  width: 39px;
  flex: none;
  padding-top: 1px;
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
}
.plan-copy {
  flex: 1;
  min-width: 0;
}
.plan-content {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
  word-break: break-all;
}
.plan-project {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 8px;
}
.plan-state {
  flex: none;
  padding: 2px 5px;
  border-radius: 4px;
  background: var(--surface-soft);
  color: var(--text-muted);
  font-size: 8px;
}
.status-row {
  display: flex;
  gap: 4px;
  margin: 9px 0 0 47px;
}
.status-button {
  min-width: 44px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 600;
}
.status-button.selected {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-deep);
}
.note-box {
  margin: 9px 0 0 47px;
  padding: 9px;
  border-radius: 7px;
  background: #f6f9f7;
}
.note-input {
  width: 100%;
  min-height: 58px;
  color: var(--text-primary);
  font-size: 12px;
  line-height: 18px;
}
.note-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 7px;
  margin-top: 7px;
}
.note-voice {
  min-height: 29px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 0 7px;
  border: 1px solid #cfe5df;
  border-radius: 5px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 8px;
  font-weight: 650;
}
.note-voice.recording,
.insight-mic.recording {
  border-color: var(--warning);
  background: var(--warning-bg);
  color: var(--warning);
  animation: soft-pulse 1.8s infinite;
}
.note-buttons {
  display: flex;
  gap: 5px;
}
.note-cancel,
.note-save {
  height: 29px;
  padding: 0 9px;
  border-radius: 5px;
  font-size: 9px;
  line-height: 29px;
}
.note-cancel {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
}
.note-save {
  background: var(--accent);
  color: #ffffff;
}
.history-note {
  display: block;
  margin: 7px 0 0 47px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 8px;
  line-height: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.empty {
  padding: 28px 0;
  color: var(--text-muted);
  font-size: 10px;
  text-align: center;
}
.insight-block {
  flex: none;
  margin-top: 12px;
  padding: 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f8faf9;
}
.insight-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 9px;
}
.insight-label {
  display: block;
  margin-top: 3px;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}
.insight-mic {
  width: 31px;
  height: 31px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #cfe5df;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.insight-input {
  width: 100%;
  min-height: 54px;
  margin-top: 9px;
  color: var(--text-primary);
  font-size: 12px;
  line-height: 19px;
}
.voice-live {
  display: block;
  margin-top: 5px;
  color: var(--accent);
  font-size: 8px;
  line-height: 14px;
}
.archive-button {
  height: 47px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 12px;
  border-radius: 8px;
  background: var(--accent);
  color: #ffffff;
  font-size: 13px;
  font-weight: 650;
  line-height: 47px;
}
.archive-button[disabled] {
  opacity: 0.55;
}
.locked-state {
  min-height: 48px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 9px 11px;
  border: 1px solid #cfe6df;
  border-radius: 8px;
  background: #f0faf6;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
}
.locked-icon {
  width: 28px;
  height: 28px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
</style>
