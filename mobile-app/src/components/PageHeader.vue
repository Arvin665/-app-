<template>
  <view class="page-header safe-top">
    <view class="header-row">
      <view class="side left" @tap="goBack">
        <ChevronLeft v-if="back !== false" :size="20" :stroke-width="2.2" />
      </view>
      <text class="title">{{ title }}</text>
      <view class="side right">
        <slot name="actions"></slot>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ChevronLeft } from "@lucide/vue";
const props = defineProps({
  title: { type: String, default: "" },
  back: { type: Boolean, default: true },
  fallback: { type: String, default: "/pages/home/index" },
});

function goBack() {
  if (props.back === false) return;
  const pages = getCurrentPages();
  if (pages.length > 1) uni.navigateBack();
  else uni.reLaunch({ url: props.fallback });
}
</script>

<style scoped>
.page-header {
  background: var(--page-bg);
  padding-left: 16px;
  padding-right: 16px;
}
.header-row {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.side {
  width: 72px;
  display: flex;
  align-items: center;
}
.side.right {
  justify-content: flex-end;
}
.back-text {
  color: var(--text-secondary);
  font-size: 14px;
}
.title {
  max-width: 190px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-row {
  min-height: 62px;
}
.side {
  width: 72px;
  flex: none;
}
.back-text {
  display: none;
}
.title {
  flex: 1;
  max-width: none;
  text-align: center;
  font-size: 19px;
  font-weight: 720;
}
</style>
