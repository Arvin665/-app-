<template>
  <div class="system-page recycle-page">
    <header class="topbar">
      <span class="topbar-title">回收站</span>
      <span class="toolbar-note">软删除数据保留 7 天</span>
      <div class="toolbar-spacer"></div>
      <el-select v-model="moduleFilter" clearable placeholder="全部模块" @change="loadRecycle">
        <el-option v-for="module in moduleList" :key="module.key" :label="module.name" :value="module.key" />
      </el-select>
      <el-button :icon="Refresh" :loading="loading" @click="loadRecycle">刷新</el-button>
    </header>

    <div class="recycle-note">
      普通成员仅能查看并恢复本人删除的数据；管理员可恢复有权限访问的团队数据。个人灵感始终仅本人可见。
    </div>

    <div class="recycle-table">
      <el-table v-loading="loading" :data="items" border height="100%">
        <el-table-column prop="module_name" label="业务模块" width="130" />
        <el-table-column label="名称 / 正文" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">{{ recordTitle(row.module, row.record) }}</template>
        </el-table-column>
        <el-table-column label="业务日期" width="120">
          <template #default="{ row }">{{ businessDate(row) }}</template>
        </el-table-column>
        <el-table-column label="删除时间" width="155">
          <template #default="{ row }">{{ formatDateTime(row.record.deleted_at) }}</template>
        </el-table-column>
        <el-table-column label="恢复截止" width="155">
          <template #default="{ row }">{{ formatDateTime(row.record.recycle_expires_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              :disabled="!row.record.can_restore"
              :loading="restoringId === row.record.record_id"
              @click="restore(row)"
            >
              {{ row.record.can_restore ? "恢复" : "无权限" }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { api } from "../services/api";
import { displayTitle, moduleList, modules } from "../data/modules";

defineProps({
  session: { type: Object, required: true },
});
const items = ref([]);
const moduleFilter = ref("");
const loading = ref(false);
const restoringId = ref("");

function formatDateTime(value) {
  return value ? String(value).replace("T", " ").slice(0, 16) : "";
}

function recordTitle(moduleKey, record) {
  return displayTitle(moduleKey, record);
}

function businessDate(row) {
  const value = row.record[modules[row.module]?.dateField] || "";
  return String(value).slice(0, 10);
}

async function loadRecycle() {
  loading.value = true;
  try {
    const query = moduleFilter.value ? `?module=${moduleFilter.value}` : "";
    const result = await api(`/recycle${query}`);
    items.value = result.items || [];
  } catch (error) {
    ElMessage.error(error.message || "回收站加载失败");
  } finally {
    loading.value = false;
  }
}

async function restore(row) {
  const confirmed = await ElMessageBox.confirm(
    `确认恢复“${recordTitle(row.module, row.record)}”？`,
    "恢复记录",
    { confirmButtonText: "恢复", cancelButtonText: "取消" },
  ).then(() => true).catch(() => false);
  if (!confirmed) return;
  restoringId.value = row.record.record_id;
  try {
    await api(`/recycle/${row.module}/${row.record.record_id}/restore`, { method: "POST" });
    ElMessage.success("记录已恢复");
    await loadRecycle();
  } catch (error) {
    ElMessage.error(error.message || "恢复失败");
  } finally {
    restoringId.value = "";
  }
}

onMounted(loadRecycle);
</script>

<style scoped>
.recycle-page {
  background: #f5f7fa;
}
.topbar .el-select {
  width: 150px;
}
.recycle-note {
  flex: none;
  padding: 10px 16px;
  background: #fff7e6;
  color: #666666;
  font-size: 11px;
  line-height: 18px;
}
.recycle-table {
  flex: 1;
  min-height: 0;
  margin: 8px;
  border: 1px solid #e5e6eb;
  background: #ffffff;
}
</style>
