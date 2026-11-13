<template>
  <view class="profile-page">
    <PageHeader title="个人中心" fallback="/pages/home/index" />

    <view class="identity">
      <text class="identity-title">团队设备 · {{ session?.role_name || "普通成员" }}</text>
      <text class="identity-note">设备已绑定，无需重复登录</text>
    </view>

    <view class="menu">
      <view class="menu-row" hover-class="menu-row-hover" @tap="goRecords">
        <text class="menu-label">我的记录</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-row" hover-class="menu-row-hover" @tap="goRecycle">
        <text class="menu-label">回收站</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-row" hover-class="menu-row-hover" @tap="goAbout">
        <text class="menu-label">关于</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import PageHeader from "../../components/PageHeader.vue";
import { ensureBound, getSession } from "../../services/session";

const session = ref(getSession());

function goRecords() {
  uni.navigateTo({ url: "/pages/history/index" });
}

function goRecycle() {
  uni.navigateTo({ url: "/pages/recycle/index" });
}

function goAbout() {
  uni.navigateTo({ url: "/pages/about/index" });
}

onShow(() => {
  if (!ensureBound()) return;
  session.value = getSession();
});
</script>

<style scoped>
.profile-page {
  width: 100vw;
  min-height: 100vh;
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--page-bg);
}
.identity {
  padding: 8px 16px 20px;
}
.identity-title {
  display: block;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
}
.identity-note {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 12px;
}
.menu {
  margin: 0 16px;
  overflow: hidden;
  border-radius: 8px;
  background: var(--surface);
}
.menu-row {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
}
.menu-row:last-child {
  border-bottom: 0;
}
.menu-row-hover {
  background: #f7f8fa;
}
.menu-label {
  color: var(--text-primary);
  font-size: 14px;
}
.menu-arrow {
  color: var(--text-muted);
  font-size: 22px;
  line-height: 22px;
}
</style>
