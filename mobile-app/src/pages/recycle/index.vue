<template>
  <view class="recycle-page">
    <PageHeader title="回收站" fallback="/pages/profile/index">
      <template #actions>
        <text class="header-action" @tap="loadRecycle">刷新</text>
      </template>
    </PageHeader>

    <view class="retention-note">仅展示最近 7 天删除的数据，恢复后回到原业务模块。</view>

    <scroll-view class="recycle-scroll" scroll-y>
      <view v-if="!items.length && !loading" class="empty-state">回收站为空</view>
      <view v-for="item in items" :key="`${item.module}-${item.record.record_id}`" class="recycle-card">
        <view class="card-head">
          <text class="module-name">{{ item.module_name }}</text>
          <text class="deleted-time">{{ formatTime(item.record.deleted_at) }}</text>
        </view>
        <text class="record-title">{{ titleOf(item) }}</text>
        <text class="record-summary">{{ summaryOf(item) }}</text>
        <view class="card-footer">
          <text class="expires">可恢复至 {{ formatTime(item.record.recycle_expires_at) }}</text>
          <button
            v-if="item.record.can_restore"
            class="restore-button"
            :disabled="restoringId === item.record.record_id"
            @tap="restore(item)"
          >
            {{ restoringId === item.record.record_id ? "恢复中" : "恢复" }}
          </button>
          <text v-else class="no-permission">无恢复权限</text>
        </view>
      </view>
      <view v-if="loading" class="loading-line">加载中...</view>
      <view class="bottom-space"></view>
    </scroll-view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { onLoad, onPullDownRefresh } from "@dcloudio/uni-app";
import PageHeader from "../../components/PageHeader.vue";
import { request } from "../../services/api";
import { recordTitle } from "../../data/modules";
import { ensureBound } from "../../services/session";

const items = ref([]);
const loading = ref(false);
const restoringId = ref("");

function titleOf(item) {
  return recordTitle(item.module, item.record);
}

function summaryOf(item) {
  if (item.module === "sale") return [item.record.district, item.record.deal_status].filter(Boolean).join(" · ");
  if (item.module === "lease") return [item.record.new_project, item.record.lease_type].filter(Boolean).join(" · ");
  if (item.module === "work") return [item.record.record_type, item.record.record_date].filter(Boolean).join(" · ");
  return [item.record.inspiration_type, item.record.record_time?.slice(0, 16)].filter(Boolean).join(" · ");
}

function formatTime(value) {
  return value ? String(value).replace("T", " ").slice(0, 16) : "";
}

async function loadRecycle() {
  if (loading.value) return;
  loading.value = true;
  try {
    const result = await request("/recycle");
    items.value = result.items || [];
  } catch (error) {
    uni.showToast({ title: error.message || "回收站加载失败", icon: "none" });
  } finally {
    loading.value = false;
  }
}

function restore(item) {
  if (!item.record.can_restore || restoringId.value) return;
  uni.showModal({
    title: "恢复记录",
    content: `确认恢复“${titleOf(item)}”？`,
    success: async (result) => {
      if (!result.confirm) return;
      restoringId.value = item.record.record_id;
      try {
        await request(`/recycle/${item.module}/${item.record.record_id}/restore`, { method: "POST" });
        items.value = items.value.filter((entry) => entry.record.record_id !== item.record.record_id);
        uni.showToast({ title: "恢复成功", icon: "success" });
      } catch (error) {
        uni.showToast({ title: error.message || "恢复失败", icon: "none" });
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
</script>

<style scoped>
.recycle-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--page-bg);
}
.header-action {
  color: var(--accent);
  font-size: 13px;
}
.retention-note {
  flex: none;
  padding: 0 16px 10px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 18px;
}
.recycle-scroll {
  flex: 1;
  min-height: 0;
}
.recycle-card {
  margin: 0 16px 12px;
  padding: 14px;
  border-radius: 8px;
  background: var(--surface);
}
.card-head,
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.module-name {
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
}
.deleted-time,
.expires,
.no-permission {
  color: var(--text-muted);
  font-size: 11px;
}
.record-title {
  display: block;
  margin-top: 8px;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 600;
  line-height: 21px;
}
.record-summary {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-footer {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.restore-button {
  width: 64px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--accent);
  border-radius: 4px;
  background: var(--surface);
  color: var(--accent);
  font-size: 12px;
  line-height: 28px;
}
.restore-button[disabled] {
  opacity: 0.5;
}
.loading-line {
  padding: 16px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}
.bottom-space {
  height: calc(24px + env(safe-area-inset-bottom));
}
</style>
