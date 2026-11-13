<template>
  <view class="app-tabbar safe-bottom">
    <view
      v-for="item in tabs"
      :key="item.key"
      class="tab-item"
      :class="{ active: active === item.key }"
      @tap="go(item)"
    >
      <view class="tab-icon">
        <component :is="item.icon" :size="21" :stroke-width="active === item.key ? 2.4 : 1.8" />
      </view>
      <text class="tab-label">{{ item.label }}</text>
    </view>
  </view>
</template>

<script setup>
import { Archive, CalendarDays, Home, UserRound } from "@lucide/vue";

defineProps({
  active: { type: String, default: "home" },
});

const tabs = [
  { key: "home", label: "首页", icon: Home, url: "/pages/home/index" },
  { key: "materials", label: "资料", icon: Archive, url: "/pages/materials/index" },
  { key: "plans", label: "计划", icon: CalendarDays, url: "/pages/plans/index" },
  { key: "profile", label: "我的", icon: UserRound, url: "/pages/profile/index" },
];

function go(item) {
  uni.reLaunch({ url: item.url });
}
</script>

<style scoped>
.app-tabbar {
  position: fixed;
  z-index: 80;
  right: 0;
  bottom: 0;
  left: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  padding-top: 8px;
  border-top: 1px solid rgba(220, 229, 225, 0.9);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 -8px 28px rgba(20, 45, 38, 0.06);
  backdrop-filter: blur(16px);
}
.tab-item {
  min-height: 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  color: var(--text-muted);
}
.tab-item.active {
  color: var(--accent);
}
.tab-icon {
  width: 26px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tab-label {
  font-size: 10px;
  font-weight: 650;
  line-height: 14px;
}
</style>
