<template>
  <view class="recycle-page app-page">
    <PageHeader title="回收站" fallback="/pages/profile/index">
      <template #actions>
        <view class="header-action pressable" @tap="loadRecycle"><RotateCcw :size="14" /><text>刷新</text></view>
      </template>
    </PageHeader>

    <scroll-view class="recycle-scroll" scroll-y>
      <view class="recycle-hero">
        <view class="hero-top">
          <view>
            <text class="hero-kicker">RECENTLY REMOVED</text>
            <text class="hero-title">先放在这里，<br />想找回时还来得及。</text>
          </view>
          <view class="hero-count"><text>{{ items.length }}</text><text>条待处理</text></view>
        </view>
        <view class="hero-note">
          <Clock3 :size="15" />
          <text>删除后的记录会保留 7 天，过期后不再显示。</text>
        </view>
      </view>

      <StatusNotice
        v-if="loadError && items.length"
        tone="warning"
        title="回收站没有完全同步"
        :message="loadError"
        action-text="重新加载"
        @action="loadRecycle"
      />
      <StatusNotice
        v-if="actionError"
        tone="error"
        title="这次恢复没有完成"
        :message="actionError"
        closeable
        @close="actionError = ''"
      />

      <view v-if="items.length" class="list-heading">
        <text class="section-kicker">TRASH ARCHIVE</text>
        <text class="section-title">最近删除</text>
      </view>

      <view v-if="items.length" class="recycle-list">
        <view v-for="item in items" :key="`${item.module}-${item.record.record_id}`" class="recycle-card">
          <view class="card-head">
            <ModuleMark :module-key="item.module" size="sm" />
            <view class="card-heading">
              <text class="module-name">{{ item.module_name }}</text>
              <text class="deleted-time">删除于 {{ formatTime(item.record.deleted_at) }}</text>
            </view>
            <text class="module-code">{{ moduleCode(item.module) }}</text>
          </view>
          <text class="record-title">{{ titleOf(item) }}</text>
          <text class="record-summary">{{ summaryOf(item) }}</text>
          <view class="card-footer">
            <view class="expires-line"><Clock3 :size="12" /><text>可恢复至 {{ formatTime(item.record.recycle_expires_at) }}</text></view>
            <button
              v-if="item.record.can_restore"
              class="restore-button pressable"
              :disabled="restoringId === item.record.record_id"
              @tap="restore(item)"
            >
              <LoaderCircle v-if="restoringId === item.record.record_id" :size="14" class="spin" />
              <RotateCcw v-else :size="14" />
              <text>{{ restoringId === item.record.record_id ? "恢复中" : "恢复" }}</text>
            </button>
            <text v-else class="no-permission">无恢复权限</text>
          </view>
        </view>
      </view>

      <StatePanel
        v-if="loading && !items.length"
        state="loading"
        title="正在查找最近删除的记录"
        description="回收站与各个资料模块正在同步。"
      />
      <StatePanel
        v-else-if="loadError && !items.length"
        state="error"
        title="回收站暂时打不开"
        :description="loadError"
        action-text="重新加载"
        secondary-text="返回我的"
        @action="loadRecycle"
        @secondary="goBack"
      />
      <StatePanel
        v-else-if="!items.length"
        state="empty"
        title="回收站是空的"
        description="删除的记录会先来到这里，7 天内都可以恢复。"
        action-text="返回我的"
        @action="goBack"
      />
      <view class="bottom-space"></view>
    </scroll-view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad, onPullDownRefresh } from "@dcloudio/uni-app";
import { Clock3, LoaderCircle, RotateCcw } from "@lucide/vue";
import ModuleMark from "../../components/ModuleMark.vue";
import PageHeader from "../../components/PageHeader.vue";
import StatePanel from "../../components/StatePanel.vue";
import StatusNotice from "../../components/StatusNotice.vue";
import { recordTitle } from "../../data/modules";
import { request } from "../../services/api";
import { ensureBound } from "../../services/session";

const items = ref([]);
const loading = ref(false);
const restoringId = ref("");
const loadError = ref("");
const actionError = ref("");

function moduleCode(module) {
  return { sale: "SALE", lease: "LEASE", work: "WORK", inspiration: "NOTE" }[module] || "ITEM";
}

function titleOf(item) {
  return recordTitle(item.module, item.record);
}

function summaryOf(item) {
  if (item.module === "sale") {
    return [item.record.district, item.record.deal_status, item.record.buyer].filter(Boolean).join(" · ") || "一条买卖资讯";
  }
  if (item.module === "lease") return [item.record.new_project, item.record.lease_type, item.record.industry].filter(Boolean).join(" · ") || "一条租赁动态";
  if (item.module === "work") return [item.record.record_type, item.record.record_date, item.record.related_project].filter(Boolean).join(" · ") || "一条工作记录";
  return [item.record.inspiration_type, item.record.tags, item.record.record_time?.slice(0, 16)].filter(Boolean).join(" · ") || "一条个人灵感";
}

function formatTime(value) {
  return value ? String(value).replace("T", " ").slice(0, 16) : "时间待确认";
}

async function loadRecycle() {
  if (loading.value) return;
  loading.value = true;
  loadError.value = "";
  try {
    const result = await request("/recycle");
    items.value = result.items || [];
  } catch (error) {
    loadError.value = error.message || "回收站加载失败，请检查网络和资料库服务。";
  } finally {
    loading.value = false;
  }
}

function restore(item) {
  if (!item.record.can_restore || restoringId.value) return;
  actionError.value = "";
  uni.showModal({
    title: "恢复记录",
    content: `确认把“${titleOf(item)}”恢复到${item.module_name}？`,
    confirmText: "恢复",
    success: async (result) => {
      if (!result.confirm) return;
      restoringId.value = item.record.record_id;
      try {
        await request(`/recycle/${item.module}/${item.record.record_id}/restore`, { method: "POST" });
        items.value = items.value.filter((entry) => entry.record.record_id !== item.record.record_id);
        uni.showToast({ title: "已经恢复", icon: "success" });
      } catch (error) {
        actionError.value = error.message || "恢复失败，请稍后重试。";
      } finally {
        restoringId.value = "";
      }
    },
  });
}

onLoad(() => {
  if (!ensureBound()) return;
  loadRecycle();
});

onPullDownRefresh(async () => {
  await loadRecycle();
  uni.stopPullDownRefresh();
});

function goBack() {
  const pages = getCurrentPages();
  if (pages.length > 1) uni.navigateBack();
  else uni.reLaunch({ url: "/pages/profile/index" });
}
</script>

<style scoped>
.recycle-page {
  height: 100vh;
  overflow: hidden;
}
.header-action {
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 6px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 650;
}
.recycle-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.recycle-hero {
  margin: 4px 16px 0;
  padding: 18px;
  border: 1px solid #d9e4e0;
  border-radius: 12px;
  background: linear-gradient(145deg, #f8fbfa 0%, #ffffff 72%);
}
.hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.hero-kicker,
.section-kicker {
  display: block;
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.11em;
}
.hero-title {
  display: block;
  margin-top: 12px;
  color: var(--ink);
  font-size: 22px;
  font-weight: 750;
  line-height: 30px;
}
.hero-count {
  width: 66px;
  height: 66px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.7);
}
.hero-count text:first-child {
  color: var(--ink);
  font-size: 21px;
  font-weight: 750;
  line-height: 24px;
}
.hero-count text:last-child {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 8px;
}
.hero-note {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding-top: 11px;
  border-top: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
}
.list-heading {
  margin: 24px 16px 0;
}
.section-title {
  display: block;
  margin-top: 3px;
  color: var(--ink);
  font-size: 18px;
  font-weight: 730;
}
.recycle-list {
  margin: 10px 16px 0;
}
.recycle-card {
  margin-bottom: 10px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.card-head {
  display: flex;
  align-items: center;
  gap: 9px;
}
.card-heading {
  flex: 1;
  min-width: 0;
}
.module-name {
  display: block;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 680;
}
.deleted-time {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 8px;
}
.module-code {
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.record-title {
  display: -webkit-box;
  margin-top: 12px;
  overflow: hidden;
  color: var(--ink);
  font-size: 14px;
  font-weight: 660;
  line-height: 21px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.record-summary {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.expires-line {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  font-size: 8px;
}
.restore-button {
  min-width: 69px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0 9px;
  border: 1px solid var(--accent);
  border-radius: 5px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 9px;
  font-weight: 650;
  line-height: 30px;
}
.restore-button[disabled] {
  opacity: 0.5;
}
.no-permission {
  flex: none;
  color: var(--text-muted);
  font-size: 8px;
}
.empty-state {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  text-align: center;
}
.empty-mark {
  width: 58px;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 17px;
  background: var(--surface);
  color: var(--accent);
  box-shadow: var(--shadow-soft);
}
.empty-title {
  margin-top: 15px;
  color: var(--ink);
  font-size: 16px;
  font-weight: 700;
}
.empty-desc {
  max-width: 255px;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 17px;
}
.loading-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 36px;
  color: var(--text-muted);
  font-size: 9px;
}
.bottom-space {
  height: calc(24px + env(safe-area-inset-bottom));
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Final readability pass. */
.recycle-hero,
.recycle-card {
  border-radius: 8px;
}
.hero-kicker,
.section-kicker {
  font-size: 10px;
  letter-spacing: 0;
}
.hero-count text:last-child,
.hero-note,
.deleted-time,
.record-summary,
.expires-line,
.no-permission {
  font-size: 11px;
}
.module-name,
.module-code {
  font-size: 12px;
}
.record-summary {
  line-height: 18px;
}
.restore-button {
  min-width: 76px;
  font-size: 12px;
}
.empty-state,
.loading-line {
  display: none;
}
@media (max-width: 360px) {
  .recycle-hero,
  .list-heading,
  .recycle-list {
    margin-left: 12px;
    margin-right: 12px;
  }
  .card-footer {
    align-items: flex-start;
  }
}
</style>
