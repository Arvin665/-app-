<template>
  <view class="history-page">
    <PageHeader title="历史记录" fallback="/pages/home/index">
      <template #actions>
        <text class="header-action" @tap="chooseFilter">{{ filterLabel }}</text>
      </template>
    </PageHeader>

    <view class="search-wrap">
      <input
        v-model="keyword"
        class="search-input"
        confirm-type="search"
        placeholder="搜索项目、企业、记录正文"
        @confirm="loadHistory"
        @input="queueSearch"
      />
    </view>

    <scroll-view class="history-scroll" scroll-y @scrolltolower="loadMore">
      <text class="scroll-tip">{{ keyword ? "搜索结果" : "下拉查看更早记录" }}</text>
      <view v-if="!items.length && !loading" class="empty-state">没有找到相关记录</view>
      <view v-for="item in items" :key="`${item.module}-${item.record_id}`" class="history-card" @tap="openDetail(item)">
        <view class="card-head">
          <text class="module-label">{{ moduleNames[item.module] }}</text>
          <text class="item-date">{{ item.displayDate }}</text>
        </view>
        <text class="item-title">{{ item.displayTitle }}</text>
        <text class="item-summary">{{ item.displaySummary || "暂无补充说明" }}</text>
      </view>
      <view v-if="loading" class="loading-line">加载中...</view>
      <view class="list-end"></view>
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad, onPullDownRefresh } from "@dcloudio/uni-app";
import PageHeader from "../../components/PageHeader.vue";
import { request } from "../../services/api";
import { cacheRecords, getCachedRecords } from "../../services/localDb";
import { moduleList, recordDate, recordTitle } from "../../data/modules";

const keyword = ref("");
const items = ref([]);
const loading = ref(false);
const selectedModule = ref("");
const page = ref(1);
const pageSize = 30;
let searchTimer = null;
const moduleNames = {
  sale: "项目买卖",
  lease: "企业租赁",
  work: "工作记录",
  inspiration: "个人灵感",
};
const filterLabel = computed(() => (selectedModule.value ? moduleNames[selectedModule.value] : "筛选"));

function summaryFor(module, record) {
  if (module === "sale") return [record.district, record.deal_total_price ? `${record.deal_total_price} 万元` : "", record.deal_status].filter(Boolean).join(" · ");
  if (module === "lease") return [record.industry, record.new_area ? `${record.new_area}㎡` : "", record.lease_type].filter(Boolean).join(" · ");
  if (module === "work") return [record.related_project, record.is_shared ? "团队共享" : "仅本人可见", record.record_type].filter(Boolean).join(" · ");
  return [record.inspiration_type, record.tags].filter(Boolean).join(" · ");
}

async function fetchModule(module, requestedPage, append) {
  try {
    const response = await request(`/${module.endpoint}?page=${requestedPage}&page_size=${pageSize}&keyword=${encodeURIComponent(keyword.value.trim())}`);
    await cacheRecords(module.key, response.items, new Date().toISOString());
    return { module: module.key, response, cached: false };
  } catch (error) {
    const cached = await getCachedRecords(module.key);
    const filtered = cached.filter((record) => !keyword.value.trim() || JSON.stringify(record).includes(keyword.value.trim()));
    return { module: module.key, response: { items: filtered.slice(0, pageSize), total: filtered.length }, cached: true };
  }
}

async function loadHistory(reset = true) {
  if (loading.value) return;
  loading.value = true;
  if (reset) {
    page.value = 1;
    items.value = [];
  }
  const configs = selectedModule.value ? [moduleList.find((item) => item.key === selectedModule.value)] : moduleList;
  const results = await Promise.all(configs.map((module) => fetchModule(module, page.value, !reset)));
  const fresh = results.flatMap(({ module, response }) =>
    response.items.map((record) => ({
      ...record,
      module,
      displayDate: String(record[moduleList.find((item) => item.key === module).dateField] || "").slice(0, 10),
      displayTitle: recordTitle(module, record),
      displaySummary: summaryFor(module, record),
    })),
  );
  const merged = reset ? fresh : [...items.value, ...fresh];
  const unique = Array.from(new Map(merged.map((item) => [`${item.module}-${item.record_id}`, item])).values());
  items.value = unique.sort((a, b) => (b.displayDate || "").localeCompare(a.displayDate || ""));
  loading.value = false;
}

function loadMore() {
  if (loading.value || selectedModule.value) return;
  const fullPage = moduleList.every((module) => page.value * pageSize < Number(items.value.filter((item) => item.module === module.key).length || 0));
  if (page.value > 1 && !fullPage) return;
  page.value += 1;
  loadHistory(false);
}

function queueSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadHistory(), 350);
}

function chooseFilter() {
  uni.showActionSheet({
    itemList: ["全部模块", ...moduleList.map((item) => item.name)],
    success: (result) => {
      selectedModule.value = result.tapIndex === 0 ? "" : moduleList[result.tapIndex - 1].key;
      loadHistory();
    },
  });
}

function openDetail(item) {
  uni.navigateTo({ url: `/pages/detail/index?module=${item.module}&id=${item.record_id}` });
}

onLoad(() => {
  loadHistory();
});

onPullDownRefresh(async () => {
  await loadHistory();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
.history-page {
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
.search-wrap {
  flex: none;
  padding: 0 16px 10px;
}
.search-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-primary);
  font-size: 13px;
}
.history-scroll {
  flex: 1;
  min-height: 0;
  padding-bottom: env(safe-area-inset-bottom);
}
.scroll-tip {
  display: block;
  padding: 0 16px 6px;
  color: var(--text-muted);
  font-size: 11px;
}
.history-card {
  margin: 0 16px 12px;
  padding: 14px;
  border-radius: 8px;
  background: var(--surface);
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.module-label {
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
}
.item-date {
  color: var(--text-muted);
  font-size: 11px;
}
.item-title {
  display: -webkit-box;
  margin-top: 8px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 600;
  line-height: 21px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.item-summary {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.loading-line {
  padding: 12px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}
.list-end {
  height: 24px;
}
</style>
