<template>
  <view class="state-panel" :class="[`state-${state}`, { compact }]">
    <view class="state-icon">
      <LoaderCircle v-if="state === 'loading'" :size="iconSize" class="spin" />
      <CircleAlert v-else-if="state === 'error'" :size="iconSize" />
      <CircleCheck v-else-if="state === 'success'" :size="iconSize" />
      <Inbox v-else :size="iconSize" />
    </view>
    <view class="state-copy">
      <text class="state-title">{{ resolvedTitle }}</text>
      <text v-if="resolvedDescription" class="state-description">{{ resolvedDescription }}</text>
    </view>
    <view v-if="actionText || secondaryText" class="state-actions">
      <button v-if="actionText" class="state-action primary pressable" @tap="$emit('action')">{{ actionText }}</button>
      <button v-if="secondaryText" class="state-action secondary pressable" @tap="$emit('secondary')">{{ secondaryText }}</button>
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";
import { CircleAlert, CircleCheck, Inbox, LoaderCircle } from "@lucide/vue";

const props = defineProps({
  state: { type: String, default: "empty" },
  title: { type: String, default: "" },
  description: { type: String, default: "" },
  actionText: { type: String, default: "" },
  secondaryText: { type: String, default: "" },
  compact: { type: Boolean, default: false },
});

defineEmits(["action", "secondary"]);

const resolvedTitle = computed(() => {
  if (props.title) return props.title;
  return {
    loading: "正在整理",
    empty: "这里还是空的",
    error: "暂时没有连上服务",
    success: "已经处理好",
  }[props.state] || "暂时没有内容";
});
const resolvedDescription = computed(() => {
  if (props.description) return props.description;
  if (props.state === "error") return "请检查网络和资料库服务后重试，已经填写的内容不会丢失。";
  if (props.state === "loading") return "请稍候，内容马上就会显示。";
  return "";
});
const iconSize = computed(() => (props.compact ? 20 : 25));
</script>

<style scoped>
.state-panel {
  min-height: 246px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 16px;
  padding: 28px 22px;
  border: 1px dashed #cfdcd7;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.54);
  text-align: center;
}
.state-panel.compact {
  min-height: 148px;
  margin: 10px 0;
  padding: 20px 16px;
}
.state-icon {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--accent);
  box-shadow: var(--shadow-soft);
}
.compact .state-icon {
  width: 42px;
  height: 42px;
}
.state-loading .state-icon {
  color: var(--accent);
  background: var(--accent-soft);
}
.state-error .state-icon {
  border-color: #ead4cf;
  background: #fff5f2;
  color: var(--danger);
}
.state-success .state-icon {
  border-color: #cfe5df;
  background: var(--accent-soft);
  color: var(--accent);
}
.state-copy {
  max-width: 300px;
  margin-top: 14px;
}
.state-title {
  display: block;
  color: var(--ink);
  font-size: 16px;
  font-weight: 700;
  line-height: 23px;
}
.state-description {
  display: block;
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 21px;
}
.state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
}
.state-action {
  min-width: 112px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 650;
  line-height: 40px;
}
.state-action.primary {
  background: var(--accent);
  color: #ffffff;
}
.state-action.secondary {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-primary);
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
