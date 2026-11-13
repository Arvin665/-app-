<template>
  <div v-loading.fullscreen.lock="booting" class="root-app">
    <div v-if="session" class="desktop-shell">
      <aside class="app-sidebar">
        <div class="brand-box">
          <text class="brand-name">商办信息资产库</text>
          <text class="brand-subtitle">团队内部 MVP 1.0</text>
        </div>

        <nav class="primary-nav">
          <button
            v-for="item in moduleList"
            :key="item.key"
            class="nav-item"
            :class="{ active: view === 'workbench' && activeModule === item.key }"
            @click="openModule(item.key)"
          >
            <el-icon><component :is="moduleIcons[item.key]" /></el-icon>
            <span>{{ item.name }}</span>
          </button>
        </nav>

        <nav class="secondary-nav">
          <button v-if="isAdmin" class="nav-item" :class="{ active: view === 'admin' }" @click="view = 'admin'">
            <el-icon><Setting /></el-icon>
            <span>管理员后台</span>
          </button>
          <button class="nav-item" :class="{ active: view === 'recycle' }" @click="view = 'recycle'">
            <el-icon><Delete /></el-icon>
            <span>回收站</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <div class="identity-line">
            <el-icon><Monitor /></el-icon>
            <div>
              <strong>{{ session.role_name }} · 已绑定</strong>
              <span>{{ deviceName }}</span>
            </div>
          </div>
          <div class="auto-launch-line">
            <span>开机自启</span>
            <el-switch v-model="autoLaunch" size="small" @change="changeAutoLaunch" />
          </div>
          <div class="sync-line" :class="{ pending: pendingQueue > 0 }">
            {{ pendingQueue ? `${pendingQueue} 条离线数据待同步` : "数据同步正常" }}
          </div>
        </div>
      </aside>

      <main class="app-main">
        <Workbench
          v-if="view === 'workbench'"
          :session="session"
          :active-module="activeModule"
          :sync-tick="syncTick"
          @change-module="activeModule = $event"
          @open-admin="view = 'admin'"
          @open-recycle="view = 'recycle'"
        />
        <AdminPanel v-else-if="view === 'admin' && isAdmin" :session="session" @open-recycle="view = 'recycle'" />
        <RecyclePanel v-else :session="session" />
      </main>
    </div>

    <BindDialog v-if="!session && !booting" @bound="handleBound" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  Briefcase,
  Collection,
  Delete,
  Monitor,
  Notebook,
  OfficeBuilding,
  Setting,
} from "@element-plus/icons-vue";
import Workbench from "./pages/Workbench.vue";
import AdminPanel from "./pages/AdminPanel.vue";
import RecyclePanel from "./pages/RecyclePanel.vue";
import BindDialog from "./components/BindDialog.vue";
import { api } from "./services/api";
import { getSession, getDeviceName, saveSession, setDeviceInfo } from "./services/device";
import { cacheAllModulesFromServer, flushOfflineQueue, getOfflineQueue } from "./services/offline";
import { moduleList } from "./data/modules";

const booting = ref(true);
const session = ref(getSession());
const activeModule = ref("sale");
const view = ref("workbench");
const syncTick = ref(0);
const pendingQueue = ref(getOfflineQueue().length);
const autoLaunch = ref(false);
const deviceName = ref(getDeviceName());
let timer = null;
let removeSyncListener = null;
let syncBusy = false;

const isAdmin = computed(() => Number(session.value?.role_level) === 1);
const moduleIcons = {
  sale: OfficeBuilding,
  lease: Briefcase,
  work: Notebook,
  inspiration: Collection,
};

function openModule(moduleKey) {
  activeModule.value = moduleKey;
  view.value = "workbench";
}

function handleBound(nextSession) {
  session.value = nextSession;
  view.value = "workbench";
  activeModule.value = "sale";
}

async function initializeDevice() {
  if (!window.desktop?.getSystemInfo) return;
  try {
    const info = await window.desktop.getSystemInfo();
    setDeviceInfo(info);
    deviceName.value = info.deviceName || getDeviceName();
    const launchState = await window.desktop.getAutoLaunch();
    autoLaunch.value = Boolean(launchState?.openAtLogin);
    removeSyncListener = window.desktop.onSyncNow(() => syncNow());
  } catch (error) {
    console.warn("桌面系统桥接不可用", error);
  }
}

async function refreshSession() {
  const local = getSession();
  if (!local?.device_id) return null;
  try {
    const fresh = await api("/auth/me");
    return saveSession(fresh);
  } catch (error) {
    if ([401, 403].includes(error.status)) return null;
    // 断网时保留本地设备身份，表格仍读取 IndexedDB/localStorage 缓存。
    return local;
  }
}

async function syncNow(showMessage = false) {
  if (syncBusy) return;
  syncBusy = true;
  try {
    const queueResult = await flushOfflineQueue();
    pendingQueue.value = queueResult.pending;
    await api("/auth/heartbeat", { method: "POST" });
    const cacheResult = await cacheAllModulesFromServer();
    syncTick.value += 1;
    if (cacheResult.failed.length) {
      console.warn("部分模块全量缓存刷新失败", cacheResult.failed);
    }
    if (showMessage) {
      if (cacheResult.failed.length) {
        ElMessage.warning(`已同步 ${queueResult.flushed} 条离线数据，${cacheResult.failed.length} 个模块缓存刷新失败`);
      } else {
        ElMessage.success(queueResult.flushed ? `已同步 ${queueResult.flushed} 条离线数据` : "同步完成");
      }
    }
  } catch (error) {
    pendingQueue.value = getOfflineQueue().length;
    if (showMessage) ElMessage.error(error.message || "同步失败");
  } finally {
    syncBusy = false;
  }
}

async function changeAutoLaunch(enabled) {
  if (!window.desktop?.setAutoLaunch) {
    ElMessage.warning("浏览器预览环境不控制系统自启，请在 Electron 客户端中设置");
    return;
  }
  try {
    await window.desktop.setAutoLaunch(enabled);
    ElMessage.success(enabled ? "已开启开机自启" : "已关闭开机自启");
  } catch (error) {
    autoLaunch.value = !enabled;
    ElMessage.error(error.message || "设置失败");
  }
}

onMounted(async () => {
  await initializeDevice();
  session.value = await refreshSession();
  booting.value = false;
  timer = setInterval(syncNow, 30000);
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  removeSyncListener?.();
});
</script>

<style scoped>
.root-app {
  width: 100vw;
  height: 100vh;
}
.desktop-shell {
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden;
  background: #f5f7fa;
}
.app-sidebar {
  width: 200px;
  flex: none;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e6eb;
  background: #ffffff;
}
.brand-box {
  height: 72px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 16px;
  border-bottom: 1px solid #e5e6eb;
}
.brand-name {
  color: #333333;
  font-size: 16px;
  font-weight: 600;
}
.brand-subtitle {
  margin-top: 5px;
  color: #999999;
  font-size: 10px;
}
.primary-nav,
.secondary-nav {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
}
.secondary-nav {
  margin-top: 8px;
  border-top: 1px solid #e5e6eb;
}
.nav-item {
  width: 100%;
  height: 42px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border: 0;
  border-left: 3px solid transparent;
  background: #ffffff;
  color: #666666;
  font-family: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.nav-item:hover {
  background: #f7f8fa;
  color: #333333;
}
.nav-item.active {
  border-left-color: #165dff;
  background: #f2f6ff;
  color: #165dff;
  font-weight: 600;
}
.sidebar-footer {
  margin-top: auto;
  padding: 12px 16px 14px;
  border-top: 1px solid #e5e6eb;
}
.identity-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #666666;
}
.identity-line .el-icon {
  margin-top: 2px;
}
.identity-line strong,
.identity-line span {
  display: block;
}
.identity-line strong {
  color: #333333;
  font-size: 11px;
  font-weight: 500;
}
.identity-line span {
  max-width: 145px;
  margin-top: 4px;
  overflow: hidden;
  color: #999999;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.auto-launch-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  color: #666666;
  font-size: 11px;
}
.sync-line {
  margin-top: 8px;
  color: #999999;
  font-size: 10px;
}
.sync-line.pending {
  color: #ff7d00;
}
.app-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
