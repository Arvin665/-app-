<template>
  <view class="page-header safe-top">
    <view class="header-row">
      <view class="side left" @tap="goBack">
        <text v-if="back !== false" class="back-text">返回</text>
      </view>
      <text class="title">{{ title }}</text>
      <view class="side right">
        <slot name="actions"></slot>
      </view>
    </view>
  </view>
</template>

<script setup>
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
</style>
