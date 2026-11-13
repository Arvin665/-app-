<template>
  <view class="home-page safe-top safe-bottom" :class="{ 'has-banner': showDailyBanner }">
    <view v-if="showDailyBanner" class="daily-banner" @tap="openDailyPlans">
      <text>今日计划尚未确认</text>
      <text class="banner-action">去确认</text>
    </view>
    <view class="home-grid">
      <view
        v-for="item in homeModules"
        :key="item.key"
        class="home-cell"
        hover-class="home-cell-hover"
        :hover-stay-time="80"
        @tap="openModule(item.key)"
      >
        <text class="cell-title">{{ item.name }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onPullDownRefresh, onShow } from "@dcloudio/uni-app";
import { ref } from "vue";
import { homeModules, localDate } from "../../data/modules";
import { ensureBound } from "../../services/session";
import { request } from "../../services/api";

const showDailyBanner = ref(false);
const today = localDate();

function openModule(module) {
  if (!ensureBound()) return;
  uni.navigateTo({ url: `/pages/entry/index?module=${module}` });
}

async function checkDailyBanner() {
  if (!ensureBound()) return;
  const now = new Date();
  if (now.getHours() < 17 || (now.getHours() === 17 && now.getMinutes() < 30)) {
    showDailyBanner.value = false;
    return;
  }
  try {
    const result = await request(`/work-logs/plans?record_date=${today}`);
    showDailyBanner.value = Boolean(result.items?.length && !result.locked);
  } catch (error) {
    showDailyBanner.value = false;
  }
}

function openDailyPlans() {
  uni.navigateTo({ url: "/pages/plans/index" });
}

onShow(checkDailyBanner);

onPullDownRefresh(() => {
  // 首页不增加可见一级入口，下拉手势进入历史记录。
  uni.navigateTo({ url: "/pages/history/index" });
  setTimeout(() => uni.stopPullDownRefresh(), 250);
});
</script>

<style scoped>
.home-page {
  --daily-banner-height: 0px;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--page-bg);
}
.home-page.has-banner {
  --daily-banner-height: 36px;
}
.daily-banner {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: var(--warning-bg);
  color: var(--warning);
  font-size: 12px;
}
.banner-action {
  font-weight: 600;
}
.home-grid {
  width: 100%;
  height: calc(100% - var(--daily-banner-height));
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 1px;
  background: var(--page-bg);
}
.home-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f1f3;
}
.home-cell-hover {
  background: #e9ebef;
}
.cell-title {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 500;
  letter-spacing: 0;
}
</style>
