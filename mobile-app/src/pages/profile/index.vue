<template>
  <view class="profile-page app-page tabbar-space">
    <view class="profile-top safe-top">
      <view class="brand-line"><view class="brand-dot"></view><text class="brand-name">YOUR LIBRARY</text></view>
      <text class="page-title">我的工作台</text>
      <text class="page-subtitle">记录、资料和每天的工作节奏，都在这里。</text>
    </view>

    <view class="identity-card">
      <view class="identity-avatar">
        <Fingerprint :size="28" :stroke-width="1.7" />
      </view>
      <view class="identity-copy">
        <text class="identity-name">{{ session?.role_name || "团队成员" }}</text>
        <text class="identity-device">{{ deviceLabel }}</text>
      </view>
      <view class="identity-status"><view class="status-dot"></view><text>已绑定</text></view>
    </view>

    <view class="stats-strip">
      <view class="stat-item">
        <text class="stat-value">{{ stats.records }}</text>
        <text class="stat-label">条业务记录</text>
      </view>
      <view class="stat-item">
        <text class="stat-value">{{ stats.materials }}</text>
        <text class="stat-label">份资料原件</text>
      </view>
      <view class="stat-item">
        <text class="stat-value">{{ pendingCount }}</text>
        <text class="stat-label">条待同步</text>
      </view>
    </view>

    <view class="menu-group">
      <text class="group-label">LIBRARY</text>
      <view class="menu-card">
        <view class="menu-row pressable" @tap="go('/pages/materials/index')">
          <view class="menu-icon tone-green"><Archive :size="19" /></view>
          <view class="menu-copy"><text class="menu-title">资料总库</text><text class="menu-note">所有图片、文件和表格</text></view>
          <ChevronRight :size="16" class="menu-arrow" />
        </view>
        <view class="menu-row pressable" @tap="go('/pages/history/index')">
          <view class="menu-icon tone-blue"><NotebookTabs :size="19" /></view>
          <view class="menu-copy"><text class="menu-title">全部记录</text><text class="menu-note">按模块和内容翻看历史</text></view>
          <ChevronRight :size="16" class="menu-arrow" />
        </view>
        <view class="menu-row pressable" @tap="go('/pages/plans/index')">
          <view class="menu-icon tone-amber"><CalendarCheck2 :size="19" /></view>
          <view class="menu-copy"><text class="menu-title">计划与复盘</text><text class="menu-note">今天的待办和每日回看</text></view>
          <ChevronRight :size="16" class="menu-arrow" />
        </view>
      </view>
    </view>

    <view class="menu-group">
      <text class="group-label">SYSTEM</text>
      <view class="menu-card">
        <view class="menu-row pressable" @tap="go('/pages/recycle/index')">
          <view class="menu-icon tone-neutral"><RotateCcw :size="19" /></view>
          <view class="menu-copy"><text class="menu-title">回收站</text><text class="menu-note">删除记录保留 7 天</text></view>
          <ChevronRight :size="16" class="menu-arrow" />
        </view>
        <view class="menu-row pressable" @tap="go('/pages/about/index')">
          <view class="menu-icon tone-neutral"><Info :size="19" /></view>
          <view class="menu-copy"><text class="menu-title">关于与能力说明</text><text class="menu-note">隐私、识别和同步边界</text></view>
          <ChevronRight :size="16" class="menu-arrow" />
        </view>
      </view>
    </view>

    <view class="profile-footer">
      <view class="footer-mark"><Boxes :size="16" /></view>
      <text>信息先被好好收下，再慢慢变成判断。</text>
    </view>

    <AppTabBar active="profile" />
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import {
  Archive,
  Boxes,
  CalendarCheck2,
  ChevronRight,
  Fingerprint,
  Info,
  NotebookTabs,
  RotateCcw,
} from "@lucide/vue";
import AppTabBar from "../../components/AppTabBar.vue";
import { moduleList } from "../../data/modules";
import { request } from "../../services/api";
import { listMaterials } from "../../services/material";
import { listOfflineQueue } from "../../services/localDb";
import { ensureBound, getSession } from "../../services/session";

const session = ref(getSession());
const stats = ref({ records: 0, materials: 0 });
const pendingCount = ref(0);
const deviceLabel = computed(() => {
  const value = session.value?.device_name || "当前设备";
  return String(value).slice(0, 34);
});

function go(url) {
  uni.navigateTo({ url });
}

async function loadProfile() {
  if (!ensureBound()) return;
  session.value = getSession();
  try {
    const [recordResults, materialResult, queue] = await Promise.all([
      Promise.all(moduleList.map((module) => request(`/${module.endpoint}?page_size=1`))),
      listMaterials({ pageSize: 1 }),
      listOfflineQueue(),
    ]);
    stats.value.records = recordResults.reduce((sum, result) => sum + Number(result.total || 0), 0);
    stats.value.materials = Number(materialResult.total || 0);
    pendingCount.value = queue.length;
  } catch (error) {
    // 断网时仍显示本页，不把缓存中的身份和使用入口隐藏。
  }
}

onShow(loadProfile);
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  padding: 0 16px;
}
.profile-top {
  padding-top: calc(22px + env(safe-area-inset-top));
}
.brand-line {
  display: flex;
  align-items: center;
  gap: 6px;
}
.brand-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
}
.brand-name {
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.12em;
}
.page-title {
  display: block;
  margin-top: 9px;
  color: var(--ink);
  font-size: 28px;
  font-weight: 780;
  line-height: 34px;
}
.page-subtitle {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 10px;
}
.identity-card {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-top: 20px;
  padding: 15px;
  border-radius: 12px;
  background: var(--ink);
  color: #ffffff;
  box-shadow: 0 12px 26px rgba(22, 34, 31, 0.16);
}
.identity-avatar {
  width: 50px;
  height: 50px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(160, 234, 218, 0.28);
  border-radius: 13px;
  background: rgba(130, 224, 204, 0.09);
  color: #bff4e8;
}
.identity-copy {
  flex: 1;
  min-width: 0;
}
.identity-name {
  display: block;
  font-size: 16px;
  font-weight: 700;
}
.identity-device {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: #abc2bb;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.identity-status {
  flex: none;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 7px;
  border-radius: 4px;
  background: rgba(142, 216, 200, 0.11);
  color: #bff4e8;
  font-size: 8px;
}
.status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #77ddc4;
}
.stats-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 13px;
  padding: 13px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.stat-item {
  padding-left: 13px;
  border-left: 1px solid var(--border);
}
.stat-item:first-child {
  padding-left: 0;
  border-left: 0;
}
.stat-value {
  display: block;
  color: var(--ink);
  font-size: 20px;
  font-weight: 750;
  line-height: 24px;
}
.stat-label {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 8px;
}
.menu-group {
  margin-top: 24px;
}
.group-label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.11em;
}
.menu-card {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.menu-row {
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 13px;
  border-bottom: 1px solid var(--border);
}
.menu-row:last-child {
  border-bottom: 0;
}
.menu-icon {
  width: 38px;
  height: 38px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}
.tone-green {
  background: var(--accent-soft);
  color: var(--accent);
}
.tone-blue {
  background: var(--work-soft);
  color: var(--work);
}
.tone-amber {
  background: var(--warning-bg);
  color: var(--warning);
}
.tone-neutral {
  background: var(--surface-soft);
  color: var(--text-secondary);
}
.menu-copy {
  flex: 1;
  min-width: 0;
}
.menu-title {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}
.menu-note {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 9px;
}
.menu-arrow {
  flex: none;
  color: var(--text-muted);
}
.profile-footer {
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 20px;
  color: var(--text-muted);
  font-size: 9px;
}
.footer-mark {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--surface-soft);
  color: var(--accent);
}
</style>
