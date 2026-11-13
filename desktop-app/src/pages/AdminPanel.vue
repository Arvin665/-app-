<template>
  <div class="system-page admin-page">
    <header class="topbar">
      <span class="topbar-title">管理员后台</span>
      <span class="toolbar-note">团队权限与数据治理</span>
      <div class="toolbar-spacer"></div>
      <el-button :icon="Refresh" :loading="loading" @click="refreshCurrent">刷新</el-button>
    </header>

    <div class="admin-layout">
      <aside class="admin-menu">
        <button
          v-for="item in menus"
          :key="item.key"
          class="admin-menu-item"
          :class="{ active: section === item.key }"
          @click="switchSection(item.key)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
      </aside>

      <main class="admin-content">
        <template v-if="section === 'overview'">
          <div class="section-heading">
            <div>
              <h2>数据概览</h2>
              <p>统计口径仅包含团队共享数据和设备状态，不读取他人私有工作记录与个人灵感。</p>
            </div>
          </div>
          <div class="stat-strip">
            <div v-for="stat in stats" :key="stat.key" class="stat-block">
              <span>{{ stat.label }}</span>
              <strong>{{ stat.value }}</strong>
              <small>{{ stat.note }}</small>
            </div>
          </div>
          <div class="overview-grid">
            <section class="flat-section">
              <h3>权限边界</h3>
              <p>管理员可管理邀请码、设备、团队共享数据和全量业务备份，但不能读取成员私有工作记录或个人灵感。</p>
            </section>
            <section class="flat-section">
              <h3>回收与备份</h3>
              <p>业务数据软删除保留 7 天。建议每日执行全量备份，并将备份文件保存到异地存储。</p>
              <el-button text type="primary" @click="switchSection('backup')">前往备份管理</el-button>
            </section>
          </div>
        </template>

        <template v-else-if="section === 'invites'">
          <div class="section-heading with-action">
            <div>
              <h2>邀请码管理</h2>
              <p>生成 6 位数字邀请码，设置有效期、使用次数和权限等级。</p>
            </div>
            <el-button type="primary" :icon="Plus" @click="openInviteDialog">生成邀请码</el-button>
          </div>
          <el-table v-loading="loading" :data="invites" border height="calc(100vh - 180px)">
            <el-table-column prop="invite_code" label="邀请码" width="100" />
            <el-table-column prop="role_level" label="权限等级" width="100">
              <template #default="{ row }">{{ Number(row.role_level) === 1 ? "管理员" : "普通成员" }}</template>
            </el-table-column>
            <el-table-column label="使用次数" width="110">
              <template #default="{ row }">{{ row.used_count }} / {{ row.max_use_count }}</template>
            </el-table-column>
            <el-table-column label="有效期" min-width="190">
              <template #default="{ row }">{{ formatDateTime(row.valid_start) }} - {{ formatDateTime(row.valid_end) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="plain">
                  {{ row.status === 1 ? "启用" : "停用" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="toggleInvite(row)">
                  {{ row.status === 1 ? "停用" : "启用" }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <template v-else-if="section === 'devices'">
          <div class="section-heading with-action">
            <div>
              <h2>设备管理</h2>
              <p>设备即团队身份。禁用后该设备立即无法继续访问后端接口。</p>
            </div>
            <div class="heading-actions">
              <el-input v-model="deviceKeyword" clearable placeholder="设备名称 / ID" @keyup.enter="loadDevices" />
              <el-button :icon="Search" @click="loadDevices">查询</el-button>
            </div>
          </div>
          <el-table v-loading="loading" :data="devices" border height="calc(100vh - 180px)">
            <el-table-column prop="device_name" label="设备名称" min-width="180" />
            <el-table-column prop="device_id" label="设备 ID" min-width="270" show-overflow-tooltip />
            <el-table-column prop="role_name" label="权限" width="90" />
            <el-table-column prop="invite_code" label="邀请码" width="90" />
            <el-table-column label="最后在线" width="155">
              <template #default="{ row }">{{ formatDateTime(row.last_online_time) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'danger'" effect="plain">
                  {{ row.status === 1 ? "正常" : "禁用" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button
                  text
                  :type="row.status === 1 ? 'danger' : 'primary'"
                  :disabled="row.device_id === session.device_id"
                  @click="toggleDevice(row)"
                >
                  {{ row.status === 1 ? "禁用" : "启用" }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <template v-else-if="section === 'logs'">
          <div class="section-heading with-action">
            <div>
              <h2>操作日志</h2>
              <p>增删改、导入和导出操作进入统一审计轨迹。</p>
            </div>
            <div class="heading-actions log-filter">
              <el-select v-model="logModule" clearable placeholder="业务模块" @change="loadLogs">
                <el-option label="项目买卖" value="sale" />
                <el-option label="企业租赁" value="lease" />
                <el-option label="工作记录" value="work" />
                <el-option label="个人灵感" value="inspiration" />
              </el-select>
              <el-select v-model="logOperation" clearable placeholder="操作类型" @change="loadLogs">
                <el-option label="新增" value="add" />
                <el-option label="更新" value="update" />
                <el-option label="删除" value="delete" />
                <el-option label="导出" value="export" />
              </el-select>
              <el-input v-model="logDevice" clearable placeholder="设备 ID" @keyup.enter="loadLogs" />
              <el-button :icon="Search" @click="loadLogs">查询</el-button>
            </div>
          </div>
          <el-table v-loading="loading" :data="logs" border height="calc(100vh - 180px)">
            <el-table-column prop="create_time" label="时间" width="155">
              <template #default="{ row }">{{ formatDateTime(row.create_time) }}</template>
            </el-table-column>
            <el-table-column prop="device_id" label="设备 ID" width="250" show-overflow-tooltip />
            <el-table-column prop="biz_module" label="模块" width="85" />
            <el-table-column prop="operation_type" label="操作" width="75" />
            <el-table-column prop="biz_record_id" label="记录 ID" width="250" show-overflow-tooltip />
            <el-table-column prop="operation_content" label="操作内容" min-width="300" show-overflow-tooltip />
            <el-table-column prop="ip_address" label="IP" width="120" />
          </el-table>
        </template>

        <template v-else>
          <div class="section-heading">
            <div>
              <h2>全量备份与恢复</h2>
              <p>备份包含管理员可见的数据、设备身份、附件原件；成员私有内容不会进入他人备份。</p>
            </div>
          </div>
          <div class="backup-layout">
            <section class="flat-section backup-block">
              <h3>下载全量备份</h3>
              <p>生成 ZIP 备份包，包含 database.json 与上传附件。建议每日执行并异地保存 30 天。</p>
              <el-button type="primary" :icon="Download" :loading="backupLoading" @click="downloadBackup">
                下载备份
              </el-button>
            </section>
            <section class="flat-section backup-block">
              <h3>合并恢复</h3>
              <p>恢复按主键合并，不覆盖邀请码与设备身份；同主键业务记录以备份内容覆盖。</p>
              <el-upload
                :auto-upload="false"
                :limit="1"
                accept=".zip"
                :on-change="onBackupFile"
                :show-file-list="true"
              >
                <el-button :icon="Upload">选择备份包</el-button>
              </el-upload>
              <el-button class="restore-button" type="warning" :loading="restoreLoading" :disabled="!backupFile" @click="restoreBackup">
                确认合并恢复
              </el-button>
            </section>
          </div>
          <el-alert
            type="warning"
            :closable="false"
            title="恢复是不可批量撤销的数据写入操作。执行前请再次确认备份包来源与版本。"
          />
        </template>
      </main>
    </div>

    <el-dialog v-model="inviteVisible" title="生成邀请码" width="460px">
      <el-form label-position="top">
        <el-form-item label="权限等级">
          <el-radio-group v-model="inviteForm.role_level">
            <el-radio :value="2">普通成员</el-radio>
            <el-radio :value="1">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="最大使用次数">
          <el-input-number v-model="inviteForm.max_use_count" :min="1" :max="10000" />
        </el-form-item>
        <el-form-item label="失效时间">
          <el-date-picker
            v-model="inviteForm.valid_end"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="默认 7 天"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inviteVisible = false">取消</el-button>
        <el-button type="primary" :loading="inviteSaving" @click="createInvite">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  DataAnalysis,
  Download,
  Key,
  List,
  Monitor,
  Plus,
  Refresh,
  Search,
  Upload,
} from "@element-plus/icons-vue";
import { api, downloadFile, uploadFile } from "../services/api";
import { localDateString } from "../utils/date";

defineProps({
  session: { type: Object, required: true },
});
const emit = defineEmits(["open-recycle"]);

const menus = [
  { key: "overview", label: "数据概览", icon: DataAnalysis },
  { key: "invites", label: "邀请码管理", icon: Key },
  { key: "devices", label: "设备管理", icon: Monitor },
  { key: "logs", label: "操作日志", icon: List },
  { key: "backup", label: "全量备份", icon: Download },
];
const section = ref("overview");
const loading = ref(false);
const overview = ref({ sale_count: 0, lease_count: 0, shared_work_count: 0, active_device_count: 0 });
const invites = ref([]);
const devices = ref([]);
const logs = ref([]);
const deviceKeyword = ref("");
const logModule = ref("");
const logOperation = ref("");
const logDevice = ref("");
const inviteVisible = ref(false);
const inviteSaving = ref(false);
const backupLoading = ref(false);
const restoreLoading = ref(false);
const backupFile = ref(null);
const inviteForm = reactive({ role_level: 2, max_use_count: 10, valid_end: "" });

const stats = computed(() => [
  { key: "sale", label: "买卖记录", value: overview.value.sale_count, note: "团队共享" },
  { key: "lease", label: "租赁记录", value: overview.value.lease_count, note: "团队共享" },
  { key: "work", label: "共享工作记录", value: overview.value.shared_work_count, note: "不含私有记录" },
  { key: "device", label: "活跃设备", value: overview.value.active_device_count, note: "状态正常" },
]);

function formatDateTime(value) {
  return value ? String(value).replace("T", " ").slice(0, 16) : "";
}

async function loadOverview() {
  loading.value = true;
  try {
    overview.value = await api("/admin/statistics");
  } catch (error) {
    ElMessage.error(error.message || "概览加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadInvites() {
  loading.value = true;
  try {
    const result = await api("/admin/invites?page_size=200");
    invites.value = result.items || [];
  } catch (error) {
    ElMessage.error(error.message || "邀请码加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadDevices() {
  loading.value = true;
  try {
    const params = new URLSearchParams({ page_size: "200" });
    if (deviceKeyword.value.trim()) params.set("keyword", deviceKeyword.value.trim());
    const result = await api(`/admin/devices?${params}`);
    devices.value = result.items || [];
  } catch (error) {
    ElMessage.error(error.message || "设备加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadLogs() {
  loading.value = true;
  try {
    const params = new URLSearchParams({ page_size: "300" });
    if (logModule.value) params.set("biz_module", logModule.value);
    if (logOperation.value) params.set("operation_type", logOperation.value);
    if (logDevice.value.trim()) params.set("target_device", logDevice.value.trim());
    const result = await api(`/admin/logs?${params}`);
    logs.value = result.items || [];
  } catch (error) {
    ElMessage.error(error.message || "操作日志加载失败");
  } finally {
    loading.value = false;
  }
}

async function refreshCurrent() {
  if (section.value === "overview") await loadOverview();
  else if (section.value === "invites") await loadInvites();
  else if (section.value === "devices") await loadDevices();
  else if (section.value === "logs") await loadLogs();
  else ElMessage.info("备份页面无列表需要刷新");
}

async function switchSection(key) {
  section.value = key;
  await refreshCurrent();
}

function openInviteDialog() {
  const expires = new Date();
  expires.setDate(expires.getDate() + 7);
  inviteForm.role_level = 2;
  inviteForm.max_use_count = 10;
  inviteForm.valid_end = `${localDateString(expires)}T23:59:59`;
  inviteVisible.value = true;
}

async function createInvite() {
  inviteSaving.value = true;
  try {
    const result = await api("/admin/invites", {
      method: "POST",
      data: {
        role_level: inviteForm.role_level,
        max_use_count: inviteForm.max_use_count,
        valid_end: inviteForm.valid_end || undefined,
      },
    });
    ElMessage.success(`邀请码已生成：${result.invite_code}`);
    inviteVisible.value = false;
    loadInvites();
  } catch (error) {
    ElMessage.error(error.message || "邀请码生成失败");
  } finally {
    inviteSaving.value = false;
  }
}

async function toggleInvite(row) {
  try {
    await api(`/admin/invites/${row.id}/status`, {
      method: "PATCH",
      data: { status: row.status === 1 ? 0 : 1 },
    });
    ElMessage.success("邀请码状态已更新");
    loadInvites();
  } catch (error) {
    ElMessage.error(error.message || "邀请码状态更新失败");
  }
}

async function toggleDevice(row) {
  const confirm = await ElMessageBox.confirm(
    row.status === 1 ? `确认禁用设备“${row.device_name || row.device_id}”？` : "确认恢复该设备访问权限？",
    "设备状态",
    { confirmButtonText: "确认", cancelButtonText: "取消", type: "warning" },
  ).then(() => true).catch(() => false);
  if (!confirm) return;
  try {
    await api(`/admin/devices/${row.device_id}/status`, {
      method: "PATCH",
      data: { status: row.status === 1 ? 0 : 1 },
    });
    ElMessage.success("设备状态已更新");
    loadDevices();
  } catch (error) {
    ElMessage.error(error.message || "设备状态更新失败");
  }
}

async function downloadBackup() {
  backupLoading.value = true;
  try {
    await downloadFile("/admin/backup", `asset_backup_${localDateString()}.zip`);
    ElMessage.success("备份已开始下载");
  } catch (error) {
    ElMessage.error(error.message || "备份下载失败");
  } finally {
    backupLoading.value = false;
  }
}

function onBackupFile(file) {
  backupFile.value = file.raw;
}

async function restoreBackup() {
  if (!backupFile.value) return;
  const confirmed = await ElMessageBox.confirm(
    "恢复会按主键合并备份数据。确认继续？",
    "合并恢复",
    { confirmButtonText: "确认恢复", cancelButtonText: "取消", type: "warning" },
  ).then(() => true).catch(() => false);
  if (!confirmed) return;
  restoreLoading.value = true;
  try {
    const result = await uploadFile("/admin/backup/restore", backupFile.value);
    ElMessage.success(`恢复完成，共合并 ${result.restored_rows} 行`);
    backupFile.value = null;
    await loadOverview();
  } catch (error) {
    ElMessage.error(error.message || "备份恢复失败");
  } finally {
    restoreLoading.value = false;
  }
}

onMounted(loadOverview);
</script>

<style scoped>
.admin-layout {
  flex: 1;
  min-height: 0;
  display: flex;
}
.admin-menu {
  width: 144px;
  flex: none;
  padding: 8px 0;
  border-right: 1px solid #e5e6eb;
  background: #ffffff;
}
.admin-menu-item {
  width: 100%;
  height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border: 0;
  border-left: 3px solid transparent;
  background: #ffffff;
  color: #666666;
  font-family: inherit;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}
.admin-menu-item:hover {
  background: #f7f8fa;
}
.admin-menu-item.active {
  border-left-color: #165dff;
  background: #f2f6ff;
  color: #165dff;
  font-weight: 600;
}
.admin-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: 16px;
  overflow: auto;
  background: #f5f7fa;
}
.section-heading {
  margin-bottom: 14px;
}
.section-heading.with-action {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.section-heading h2 {
  margin: 0;
  color: #333333;
  font-size: 17px;
  font-weight: 600;
}
.section-heading p {
  margin: 6px 0 0;
  color: #666666;
  font-size: 11px;
  line-height: 18px;
}
.stat-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  border: 1px solid #e5e6eb;
  background: #e5e6eb;
}
.stat-block {
  min-height: 104px;
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: #ffffff;
}
.stat-block span {
  color: #666666;
  font-size: 11px;
}
.stat-block strong {
  margin-top: 9px;
  color: #333333;
  font-size: 26px;
  font-weight: 500;
}
.stat-block small {
  margin-top: auto;
  color: #999999;
  font-size: 10px;
}
.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}
.flat-section {
  padding: 16px;
  border: 1px solid #e5e6eb;
  background: #ffffff;
}
.flat-section h3 {
  margin: 0;
  color: #333333;
  font-size: 13px;
  font-weight: 600;
}
.flat-section p {
  margin: 9px 0 0;
  color: #666666;
  font-size: 11px;
  line-height: 19px;
}
.heading-actions {
  display: flex;
  gap: 8px;
}
.heading-actions .el-input {
  width: 220px;
}
.log-filter .el-select {
  width: 120px;
}
.backup-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.backup-block {
  min-height: 190px;
}
.backup-block .el-button {
  margin-top: 18px;
}
.restore-button {
  margin-left: 8px;
}
:deep(.el-upload) {
  display: inline-flex;
  margin-top: 16px;
}
</style>
