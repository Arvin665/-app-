<template>
  <view class="status-notice" :class="[`tone-${tone}`, { compact }]">
    <view class="notice-icon">
      <component :is="noticeIcon" :size="compact ? 17 : 19" :stroke-width="2.1" />
    </view>
    <view class="notice-copy">
      <text v-if="title" class="notice-title">{{ title }}</text>
      <text v-if="message" class="notice-message">{{ message }}</text>
    </view>
    <button v-if="actionText" class="notice-action pressable" @tap="$emit('action')">{{ actionText }}</button>
    <view v-if="closeable" class="notice-close pressable" @tap="$emit('close')">
      <X :size="16" />
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";
import { BellRing, CircleAlert, CircleCheck, Info, TriangleAlert, X } from "@lucide/vue";

const props = defineProps({
  tone: { type: String, default: "info" },
  title: { type: String, default: "" },
  message: { type: String, default: "" },
  actionText: { type: String, default: "" },
  closeable: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
});

defineEmits(["action", "close"]);

const noticeIcon = computed(() => ({
  info: Info,
  success: CircleCheck,
  warning: TriangleAlert,
  error: CircleAlert,
  reminder: BellRing,
}[props.tone] || Info));
</script>

<style scoped>
.status-notice {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 10px 16px 0;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.status-notice.compact {
  align-items: center;
  padding: 10px 11px;
}
.notice-icon {
  width: 30px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--text-secondary);
}
.compact .notice-icon {
  width: 28px;
  height: 28px;
}
.notice-copy {
  min-width: 0;
  flex: 1;
}
.notice-title {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
  line-height: 19px;
}
.notice-message {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 19px;
  word-break: break-word;
}
.notice-action {
  min-height: 32px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 10px;
  border: 1px solid currentColor;
  border-radius: 7px;
  background: transparent;
  color: inherit;
  font-size: 12px;
  font-weight: 650;
  line-height: 30px;
}
.notice-close {
  width: 28px;
  height: 28px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}
.tone-info {
  border-color: #d5e1e8;
  background: #f6fafc;
}
.tone-info .notice-icon {
  background: #e6f0f5;
  color: #416f89;
}
.tone-success {
  border-color: #cfe5df;
  background: #f2faf7;
}
.tone-success .notice-icon {
  background: var(--accent-soft);
  color: var(--accent);
}
.tone-warning {
  border-color: #ead7c5;
  background: #fffaf4;
}
.tone-warning .notice-icon {
  background: var(--warning-bg);
  color: var(--warning);
}
.tone-error {
  border-color: #ead4cf;
  background: #fff7f5;
}
.tone-error .notice-icon {
  background: #f9e9e5;
  color: var(--danger);
}
.tone-reminder {
  border-color: #cfe5df;
  background: #f2faf7;
}
.tone-reminder .notice-icon {
  background: var(--accent-soft);
  color: var(--accent);
}
</style>
