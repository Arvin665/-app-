<template>
  <div class="system-page workbench">
    <header class="topbar">
      <div class="title-block">
        <span class="topbar-title">{{ config.name }}</span>
        <span class="toolbar-note">共 {{ total }} 条 · {{ networkOnline ? "服务在线" : "本地缓存" }}</span>
      </div>

      <el-input
        v-model="filters.keyword"
        class="search-box"
        clearable
        :prefix-icon="Search"
        placeholder="搜索名称、企业、正文"
        @input="debounceSearch"
        @clear="loadRecords"
      />
      <el-date-picker
        v-model="filters.dateRange"
        class="range-picker"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        unlink-panels
        @change="reload"
      />
      <el-button :icon="Filter" @click="advancedVisible = true">高级筛选</el-button>

      <template v-if="selectedRows.length">
        <el-button :icon="PriceTag" @click="batchTagVisible = true">批量标签</el-button>
        <el-button :icon="Delete" type="danger" plain @click="batchDelete">批量删除</el-button>
      </template>

      <div class="toolbar-spacer"></div>
      <el-tooltip content="刷新当前模块">
        <el-button :icon="Refresh" circle :loading="loading" @click="loadRecords" />
      </el-tooltip>
      <el-tooltip content="Excel 导入">
        <el-button :icon="Upload" @click="importVisible = true">导入</el-button>
      </el-tooltip>
      <el-tooltip content="Excel 导出">
        <el-button :icon="Download" @click="exportVisible = true">导出</el-button>
      </el-tooltip>
      <el-button v-if="isAdmin" :icon="DocumentChecked" @click="downloadBackup">手动备份</el-button>
    </header>

    <div v-if="activeModule === 'work'" class="sub-toolbar">
      <el-radio-group v-model="workView" size="small" @change="reload">
        <el-radio-button value="all">全部记录</el-radio-button>
        <el-radio-button value="plans">待办计划</el-radio-button>
      </el-radio-group>
      <el-button v-if="workView === 'plans'" size="small" :icon="Calendar" @click="dailyVisible = true">
        每日确认
      </el-button>
      <span class="sub-toolbar-note">待办计划状态：未做 / 正在做 / 已做好 / 计划搁置</span>
    </div>

    <div class="table-area">
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="tableRows"
        border
        highlight-current-row
        height="100%"
        row-key="record_id"
        :default-sort="{ prop: config.dateField, order: 'descending' }"
        @selection-change="selectedRows = $event"
        @row-click="openDetail"
        @row-dblclick="openDetailEdit"
        @sort-change="sortChange"
      >
        <el-table-column type="selection" width="40" fixed="left" />
        <el-table-column
          v-for="column in visibleColumns"
          :key="column"
          :prop="column"
          :label="fieldOf(column).label"
          :width="columnWidth(column)"
          :min-width="columnMinWidth(column)"
          :fixed="column === config.nameField ? 'left' : false"
          sortable="custom"
          show-overflow-tooltip
        >
          <template #header>
            <span class="header-with-filter">
              <span>{{ fieldOf(column).label }}</span>
              <el-popover trigger="click" placement="bottom-start" :width="220">
                <template #reference>
                  <el-icon
                    class="filter-icon"
                    :class="{ active: Boolean(headerFilters[column]) }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="column-filter">
                  <div class="column-filter-title">筛选 {{ fieldOf(column).label }}</div>
                  <el-input
                    v-model="filterDrafts[column]"
                    size="small"
                    clearable
                    placeholder="包含文字"
                    @keyup.enter="applyHeaderFilter(column)"
                  />
                  <div class="column-filter-actions">
                    <el-button size="small" @click="clearHeaderFilter(column)">清除</el-button>
                    <el-button size="small" type="primary" @click="applyHeaderFilter(column)">应用</el-button>
                  </div>
                </div>
              </el-popover>
            </span>
          </template>
          <template #default="{ row }">
            <span :class="{ 'warning-text': column === 'deal_status' && row[column] === '已终止' }">
              {{ formatCell(activeModule, column, row[column]) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <footer class="table-footer">
      <div class="footer-left">
        <span v-if="selectedRows.length">已选 {{ selectedRows.length }} 条</span>
        <span v-if="Object.values(headerFilters).some(Boolean)">表头筛选生效</span>
        <span v-if="lastSyncTime">更新于 {{ lastSyncTime }}</span>
      </div>
      <div class="footer-right">
        <el-button :icon="Setting" text @click="columnSettingsVisible = true">列设置</el-button>
        <el-pagination
          v-model:current-page="filters.page"
          v-model:page-size="filters.pageSize"
          :page-sizes="[50, 100, 200, 500]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @current-change="loadRecords"
          @size-change="reload"
        />
      </div>
    </footer>

    <DetailDrawer
      v-model="detailVisible"
      :module="activeModule"
      :record="currentRecord"
      :start-editing="startEditing"
      :role-level="Number(session.role_level)"
      @saved="recordSaved"
      @deleted="recordDeleted"
    />

    <ImportDialog v-model="importVisible" :module="activeModule" @imported="loadRecords" />
    <ExportDialog v-model="exportVisible" :module="activeModule" :default-keyword="filters.keyword" />
    <BatchTagDialog
      v-model="batchTagVisible"
      :module="activeModule"
      :ids="selectedRows.map((item) => item.record_id)"
      @tagged="loadRecords"
    />
    <ColumnSettings
      v-model="columnSettingsVisible"
      :module="activeModule"
      :visible-columns="visibleColumns"
      @saved="saveColumns"
    />
    <DailyConfirmModal
      v-model="dailyVisible"
      :record-date="today"
      @archived="dailyArchived"
      @update:model-value="onDailyVisibility"
    />

    <el-dialog v-model="advancedVisible" title="高级筛选" width="520px">
      <el-form label-position="top">
        <el-form-item v-for="key in config.advancedFilters" :key="key" :label="fieldOf(key).label">
          <el-select
            v-if="fieldOf(key).type === 'select'"
            v-model="advancedFilters[key]"
            clearable
            placeholder="全部"
          >
            <el-option
              v-for="(option, index) in fieldOf(key).options"
              :key="option"
              :label="option"
              :value="fieldOf(key).optionValues ? fieldOf(key).optionValues[index] : option"
            />
          </el-select>
          <el-input
            v-else-if="key !== 'is_shared'"
            v-model="advancedFilters[key]"
            clearable
            placeholder="包含文字"
          />
          <el-select v-else v-model="advancedFilters[key]" clearable placeholder="全部">
            <el-option label="团队共享" :value="1" />
            <el-option label="仅本人可见" :value="0" />
          </el-select>
        </el-form-item>
        <el-divider content-position="left">周期筛选</el-divider>
        <div class="period-row">
          <el-select v-model="filters.periodType" clearable placeholder="全部时间">
            <el-option label="按日" value="day" />
            <el-option label="按周" value="week" />
            <el-option label="按月" value="month" />
            <el-option label="按季度" value="quarter" />
            <el-option label="按年度" value="year" />
          </el-select>
          <el-input v-model="filters.periodValue" :disabled="!filters.periodType" placeholder="周期值" />
        </div>
      </el-form>
      <template #footer>
        <el-button @click="resetAdvanced">重置</el-button>
        <el-button type="primary" @click="applyAdvanced">应用筛选</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Calendar,
  Delete,
  DocumentChecked,
  Download,
  Filter,
  PriceTag,
  Refresh,
  Search,
  Setting,
  Upload,
} from "@element-plus/icons-vue";
import DetailDrawer from "../components/DetailDrawer.vue";
import DailyConfirmModal from "../components/DailyConfirmModal.vue";
import ImportDialog from "../components/ImportDialog.vue";
import ExportDialog from "../components/ExportDialog.vue";
import BatchTagDialog from "../components/BatchTagDialog.vue";
import ColumnSettings from "../components/ColumnSettings.vue";
import { api, downloadFile, isNetworkError } from "../services/api";
import {
  cacheModuleFromServer,
  getCacheMeta,
  getCachedRecords,
  removeCachedRecord,
  upsertCachedRecord,
} from "../services/offline";
import { formatCell, modules } from "../data/modules";
import { localDateString } from "../utils/date";

const props = defineProps({
  session: { type: Object, required: true },
  activeModule: { type: String, required: true },
  syncTick: Number,
});
const emit = defineEmits(["change-module", "open-admin", "open-recycle"]);

const config = computed(() => modules[props.activeModule]);
const isAdmin = computed(() => Number(props.session.role_level) === 1);
const tableRef = ref(null);
const records = ref([]);
const total = ref(0);
const loading = ref(false);
const networkOnline = ref(true);
const selectedRows = ref([]);
const currentRecord = ref(null);
const detailVisible = ref(false);
const startEditing = ref(false);
const importVisible = ref(false);
const exportVisible = ref(false);
const batchTagVisible = ref(false);
const columnSettingsVisible = ref(false);
const advancedVisible = ref(false);
const dailyVisible = ref(false);
const workView = ref("all");
const lastSyncTime = ref("");
const today = ref(localDateString());
const filters = reactive({
  keyword: "",
  dateRange: [],
  page: 1,
  pageSize: 100,
  periodType: "",
  periodValue: "",
});
const advancedFilters = reactive({});
const headerFilters = reactive({});
const filterDrafts = reactive({});
const sortState = reactive({ prop: "", order: "" });
const columnsByModule = reactive({});
let searchTimer = null;
let loadRequestId = 0;
let clock = null;
let dailyCheckBusy = false;

const visibleColumns = computed(() => columnsByModule[props.activeModule] || config.value.defaultColumns);

const tableRows = computed(() => {
  let rows = [...records.value];
  Object.entries(headerFilters).forEach(([key, needle]) => {
    if (!needle) return;
    const text = String(needle).toLowerCase();
    rows = rows.filter((row) => String(row[key] ?? "").toLowerCase().includes(text));
  });
  if (sortState.prop && sortState.order) {
    const direction = sortState.order === "ascending" ? 1 : -1;
    rows.sort((a, b) => {
      const left = a[sortState.prop] ?? "";
      const right = b[sortState.prop] ?? "";
      return String(left).localeCompare(String(right), "zh-CN", { numeric: true }) * direction;
    });
  }
  return rows;
});

function fieldOf(key) {
  return config.value.fields.find((field) => field.key === key) || { key, label: key, type: "text" };
}

function columnWidth(key) {
  if (key === config.value.nameField) return 180;
  if (["remark", "content", "move_reason", "ext_field_1"].includes(key)) return 220;
  if (["deal_date", "start_date", "record_date", "record_time"].includes(key)) return 116;
  if (key === "tags") return 150;
  return 130;
}

function columnMinWidth(key) {
  return key === config.value.nameField ? 180 : 100;
}

function ensureColumnState() {
  if (!columnsByModule[props.activeModule]) {
    const saved = JSON.parse(localStorage.getItem(`asset-columns-${props.activeModule}`) || "null");
    columnsByModule[props.activeModule] = saved?.length ? saved : [...config.value.defaultColumns];
  }
}

function saveColumns(columns) {
  const nameField = config.value.nameField;
  const next = columns.includes(nameField) ? columns : [nameField, ...columns];
  columnsByModule[props.activeModule] = next;
  localStorage.setItem(`asset-columns-${props.activeModule}`, JSON.stringify(next));
  ElMessage.success("列设置已应用");
}

function queryString() {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  if (filters.keyword.trim()) params.set("keyword", filters.keyword.trim());
  if (filters.dateRange?.[0]) params.set("start_date", filters.dateRange[0]);
  if (filters.dateRange?.[1]) params.set("end_date", filters.dateRange[1]);
  if (filters.periodType) params.set("period_type", filters.periodType);
  if (filters.periodValue.trim()) params.set("period_value", filters.periodValue.trim());
  if (props.activeModule === "work" && workView.value === "plans") params.set("record_type", "待办计划");
  Object.entries(advancedFilters).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) params.set(key, value);
  });
  return params.toString();
}

async function loadRecords() {
  const requestId = ++loadRequestId;
  const moduleKey = props.activeModule;
  loading.value = true;
  try {
    const response = await api(`/${modules[moduleKey].endpoint}?${queryString()}`);
    if (requestId !== loadRequestId || moduleKey !== props.activeModule) return;
    records.value = response.items || [];
    total.value = Number(response.total || 0);
    networkOnline.value = true;
    try {
      await cacheModuleFromServer(moduleKey);
    } catch (cacheError) {
      console.warn("全量离线缓存刷新失败，保留已有缓存", cacheError);
    }
    if (requestId !== loadRequestId || moduleKey !== props.activeModule) return;
    lastSyncTime.value = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  } catch (error) {
    if (requestId !== loadRequestId || moduleKey !== props.activeModule) return;
    const cached = getCachedRecords(moduleKey);
    records.value = cached;
    total.value = cached.length;
    networkOnline.value = false;
    const meta = getCacheMeta(moduleKey);
    lastSyncTime.value = meta?.serverTime ? new Date(meta.serverTime).toLocaleString("zh-CN") : "";
    if (!isNetworkError(error)) ElMessage.error(error.message || "数据加载失败");
  } finally {
    if (requestId !== loadRequestId) return;
    loading.value = false;
    ensureColumnState();
    if (props.activeModule === "work") checkDailyPrompt();
  }
}

function reload() {
  filters.page = 1;
  loadRecords();
}

function debounceSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(reload, 350);
}

function applyAdvanced() {
  advancedVisible.value = false;
  reload();
}

function resetAdvanced() {
  Object.keys(advancedFilters).forEach((key) => delete advancedFilters[key]);
  filters.periodType = "";
  filters.periodValue = "";
  reload();
}

function applyHeaderFilter(key) {
  if (filterDrafts[key]?.trim()) headerFilters[key] = filterDrafts[key].trim();
  else delete headerFilters[key];
  selectedRows.value = [];
}

function clearHeaderFilter(key) {
  filterDrafts[key] = "";
  delete headerFilters[key];
}

function sortChange({ prop, order }) {
  sortState.prop = prop || "";
  sortState.order = order || "";
}

function openDetail(row) {
  currentRecord.value = row;
  startEditing.value = false;
  detailVisible.value = true;
}

function openDetailEdit(row) {
  currentRecord.value = row;
  startEditing.value = true;
  detailVisible.value = true;
}

function recordSaved(updated) {
  if (!updated) return;
  records.value = records.value.map((row) => (row.record_id === updated.record_id ? { ...row, ...updated } : row));
  currentRecord.value = { ...(currentRecord.value || {}), ...updated };
  upsertCachedRecord(props.activeModule, updated);
}

function recordDeleted(recordId) {
  records.value = records.value.filter((row) => row.record_id !== recordId);
  total.value = Math.max(total.value - 1, 0);
  removeCachedRecord(props.activeModule, recordId);
}

async function batchDelete() {
  const ids = selectedRows.value.map((row) => row.record_id);
  const confirmed = await ElMessageBox.confirm(
    `选中的 ${ids.length} 条记录将移入回收站，7 天内可恢复。`,
    "批量删除",
    { confirmButtonText: "确认删除", cancelButtonText: "取消", type: "warning" },
  ).then(() => true).catch(() => false);
  if (!confirmed) return;
  try {
    const result = await api("/batch/delete", {
      method: "POST",
      data: { module: props.activeModule, record_ids: ids },
    });
    ElMessage.success(`已删除 ${result.deleted_count} 条${result.denied.length ? `，${result.denied.length} 条无权限` : ""}`);
    (result.deleted || []).forEach((recordId) => removeCachedRecord(props.activeModule, recordId));
    tableRef.value?.clearSelection();
    loadRecords();
  } catch (error) {
    ElMessage.error(error.message || "批量删除失败");
  }
}

async function downloadBackup() {
  try {
    await downloadFile("/admin/backup", `asset_backup_${localDateString()}.zip`);
    ElMessage.success("全量备份已开始下载");
  } catch (error) {
    ElMessage.error(error.message || "备份失败");
  }
}

function checkDailyPrompt() {
  if (dailyCheckBusy || props.activeModule !== "work" || dailyVisible.value) return;
  today.value = localDateString();
  const now = new Date();
  if (now.getHours() < 17 || (now.getHours() === 17 && now.getMinutes() < 30)) return;
  const dismissed = sessionStorage.getItem(`desktop-daily-dismissed-${today.value}`);
  if (dismissed) return;
  dailyCheckBusy = true;
  api(`/work-logs/plans?record_date=${today.value}`)
    .then((result) => {
      if (result.items?.length && !result.locked) dailyVisible.value = true;
    })
    .catch(() => {})
    .finally(() => { dailyCheckBusy = false; });
}

function onDailyVisibility(visible) {
  if (!visible) sessionStorage.setItem(`desktop-daily-dismissed-${today.value}`, "1");
}

async function dailyArchived() {
  sessionStorage.setItem(`desktop-daily-dismissed-${today.value}`, "1");
  await loadRecords();
}

watch(
  () => props.activeModule,
  () => {
    ensureColumnState();
    selectedRows.value = [];
    sortState.prop = "";
    sortState.order = "";
    workView.value = "all";
    Object.keys(headerFilters).forEach((key) => delete headerFilters[key]);
    Object.keys(filterDrafts).forEach((key) => delete filterDrafts[key]);
    Object.keys(advancedFilters).forEach((key) => delete advancedFilters[key]);
    filters.keyword = "";
    filters.dateRange = [];
    filters.periodType = "";
    filters.periodValue = "";
    filters.page = 1;
    loadRecords();
  },
);

watch(
  () => props.syncTick,
  () => loadRecords(),
);

onMounted(() => {
  ensureColumnState();
  loadRecords();
  clock = setInterval(checkDailyPrompt, 60000);
});

onBeforeUnmount(() => {
  clearTimeout(searchTimer);
  if (clock) clearInterval(clock);
});
</script>

<style scoped>
.workbench {
  background: #f5f7fa;
}
.title-block {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 210px;
}
.search-box {
  width: 220px;
}
.range-picker {
  width: 240px;
}
.sub-toolbar {
  height: 40px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid #e5e6eb;
  background: #ffffff;
}
.sub-toolbar-note {
  margin-left: auto;
  color: #999999;
  font-size: 10px;
}
.table-area {
  flex: 1;
  min-height: 0;
  margin: 8px 8px 0;
  border: 1px solid #e5e6eb;
  background: #ffffff;
}
.header-with-filter {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 3px;
}
.filter-icon {
  flex: none;
  color: #bcbcbc;
  font-size: 11px;
}
.filter-icon:hover,
.filter-icon.active {
  color: #ffffff;
}
.filter-icon.active {
  color: #91b5ff;
}
.column-filter-title {
  margin-bottom: 8px;
  color: #333333;
  font-size: 12px;
  font-weight: 600;
}
.column-filter-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
.table-footer {
  height: 40px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  border-top: 1px solid #e5e6eb;
  background: #ffffff;
}
.footer-left,
.footer-right {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #999999;
  font-size: 10px;
}
.period-row {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 8px;
}
:deep(.el-table .offline-row) {
  color: #ff7d00;
}
@media (max-width: 1450px) {
  .range-picker {
    width: 210px;
  }
  .search-box {
    width: 180px;
  }
  .toolbar-note {
    display: none;
  }
}
</style>
