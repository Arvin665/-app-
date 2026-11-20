<template>
  <view class="splash-page" :class="{ leaving }">
    <text class="splash-title">Just say it.</text>
  </view>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { checkBinding, getSession } from "../../services/session";

const leaving = ref(false);
let fadeTimer = null;
let routeTimer = null;
let checkedSession;
let checkFinished = false;
let navigated = false;

function appGlobalData() {
  try {
    return getApp()?.globalData || null;
  } catch (error) {
    return null;
  }
}

function hasDirectEntry() {
  return Boolean(appGlobalData()?.splashHandled);
}

function isSplashPage() {
  const pages = getCurrentPages();
  const current = pages[pages.length - 1];
  return !current?.route || current.route === "pages/splash/index";
}

function enterApp() {
  if (navigated || hasDirectEntry() || !isSplashPage()) return;
  navigated = true;
  const globalData = appGlobalData();
  if (globalData) globalData.splashHandled = true;
  // 启动页和主页面都使用浅色状态栏，避免原生端切换时闪烁。
  // #ifdef APP-PLUS
  plus.navigator.setStatusBarBackground("#F2F5F3");
  plus.navigator.setStatusBarStyle("dark");
  // #endif
  const session = checkFinished ? checkedSession : getSession();
  uni.reLaunch({ url: session?.device_id ? "/pages/home/index" : "/pages/bind/index" });
}

onMounted(() => {
  // #ifdef APP-PLUS
  plus.navigator.setStatusBarBackground("#F2F5F3");
  plus.navigator.setStatusBarStyle("dark");
  // #endif
  checkBinding()
    .then((session) => {
      checkedSession = session;
      checkFinished = true;
    })
    .catch(() => {
      checkedSession = getSession();
      checkFinished = true;
    });
  fadeTimer = setTimeout(() => {
    leaving.value = true;
  }, 2050);
  routeTimer = setTimeout(enterApp, 2400);
});

onBeforeUnmount(() => {
  if (fadeTimer) clearTimeout(fadeTimer);
  if (routeTimer) clearTimeout(routeTimer);
});
</script>

<style scoped>
.splash-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #f2f5f3;
}
.splash-title {
  color: #16221f;
  font-family: "Avenir Next", "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 36px;
  font-weight: 560;
  line-height: 1.2;
  letter-spacing: 0;
  opacity: 0;
  animation: splash-arrive 620ms cubic-bezier(0.22, 1, 0.36, 1) 80ms forwards;
  transition: opacity 350ms ease, transform 350ms cubic-bezier(0.4, 0, 0.2, 1);
}
.splash-page.leaving .splash-title {
  opacity: 0;
  transform: translateY(-8px);
}
@keyframes splash-arrive {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (max-width: 360px) {
  .splash-title { font-size: 32px; }
}
@media (prefers-reduced-motion: reduce) {
  .splash-title { animation-duration: 1ms; transition-duration: 1ms; }
}
</style>
