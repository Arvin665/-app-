<template>
  <view class="bind-page app-page safe-top safe-bottom">
    <view class="brand-block">
      <view class="brand-line"><view class="brand-dot"></view><text class="brand-name">Sayo</text><text class="brand-suffix">Sense</text></view>
      <text class="brand-title">把知道的，<br />留在自己的资料库里。</text>
      <text class="brand-desc">项目、企业、工作和灵感，先说下来，再慢慢整理。</text>
    </view>

    <view class="module-preview">
      <view class="preview-item" v-for="item in previewModules" :key="item.key">
        <ModuleMark :module-key="item.key" size="md" />
        <view class="preview-copy">
          <text class="preview-title">{{ item.visual.short }}</text>
          <text class="preview-kicker">{{ item.visual.kicker }}</text>
        </view>
      </view>
    </view>

    <view class="bind-panel">
      <view class="panel-head">
        <view class="panel-icon"><KeyRound :size="20" /></view>
        <view>
          <text class="panel-title">进入团队资料库</text>
          <text class="panel-desc">输入管理员提供的 6 位邀请码，设备只需绑定一次。</text>
        </view>
      </view>

      <view class="code-shell">
        <view class="code-head">
          <text class="code-label">邀请码</text>
          <text class="code-count">{{ inviteCode.length }} / 6</text>
        </view>
        <input
          v-model="inviteCode"
          class="code-input"
          type="number"
          maxlength="6"
          placeholder="请输入 6 位数字"
          placeholder-style="color: #87948f; font-size: 14px; font-weight: 500; letter-spacing: 0;"
          @input="filterCode"
          @confirm="submit"
        />
        <view class="code-progress">
          <view v-for="index in 6" :key="index" class="progress-dot" :class="{ filled: inviteCode.length >= index }"></view>
        </view>
      </view>

      <view class="service-status pressable" @tap="serverExpanded = !serverExpanded">
        <view class="service-icon"><Server :size="16" /></view>
        <view class="service-copy">
          <text class="service-title">资料库服务</text>
          <text class="service-state" :class="{ ready: serviceProbe?.ok, failed: serviceProbe && !serviceProbe.ok }">
            {{ probing ? "正在检测连接..." : serviceProbe?.ok ? "已连接" : "未连接" }}
          </text>
        </view>
        <text class="service-action">{{ serverExpanded ? "收起" : "设置" }}</text>
      </view>
      <view v-if="serverExpanded" class="server-editor">
        <input
          v-model="serverAddress"
          class="server-input"
          placeholder="例如 https://asset.example.com"
          placeholder-style="color: #80958d;"
        />
        <view class="server-actions">
          <button class="server-button primary pressable" :disabled="probing" @tap="saveServer">保存并检测</button>
          <button class="server-button pressable" :disabled="probing" @tap="probe">重新检测</button>
        </view>
        <text v-if="serviceProbe?.message" class="server-hint">{{ serviceProbe.message }}</text>
      </view>
      <view v-if="serviceProbe && !serviceProbe.ok && !serverExpanded" class="service-failure">
        <CircleAlert :size="16" />
        <text>{{ serviceProbe.message }}</text>
        <button class="failure-retry pressable" :disabled="probing" @tap="retryService">重新检测</button>
      </view>

      <view v-if="bootstrapInviteHint" class="bootstrap-hint">
        <view class="hint-copy">
          <text class="hint-label">本地首次使用</text>
          <view class="hint-line">
            <text class="hint-code">{{ bootstrapInviteHint }}</text>
            <text class="hint-desc">默认管理员邀请码</text>
          </view>
        </view>
        <button class="hint-fill pressable" @tap="fillBootstrapInvite">
          <Check :size="14" />
          <text>一键填入</text>
        </button>
      </view>

      <view v-if="errorMessage" class="error-banner">
        <CircleAlert :size="18" class="error-icon" />
        <view class="error-copy">
          <text class="error-title">{{ errorIsConnection ? "没有连上资料库服务" : "邀请码没有通过验证" }}</text>
          <text class="error-message">{{ errorMessage }}</text>
        </view>
        <button v-if="errorIsConnection" class="error-retry pressable" :disabled="probing" @tap="retryService">
          <RotateCcw :size="14" />
          <text>检测</text>
        </button>
      </view>

      <button class="bind-button pressable" :disabled="loading || inviteCode.length !== 6" @tap="submit">
        <LoaderCircle v-if="loading" :size="18" class="spin" />
        <ArrowRight v-else :size="18" />
        <text>{{ loading ? "正在验证" : "验证并进入" }}</text>
      </button>
    </view>

    <view class="security-note">
      <ShieldCheck :size="16" />
      <text>资料默认只对团队开放，个人灵感只属于你自己。</text>
    </view>

    <view class="access-help">
      <view class="access-help-head">
        <view class="access-help-icon"><HelpCircle :size="18" /></view>
        <view>
          <text class="access-help-title">邀请码从哪里来</text>
          <text class="access-help-note">先确认自己该用哪一种，再输入。</text>
        </view>
      </view>
      <view class="access-help-row">
        <text class="access-help-label">首次部署</text>
        <text class="access-help-value">后端默认是 246810；如果改过 BOOTSTRAP_INVITE_CODE，以新值为准。</text>
      </view>
      <view class="access-help-row">
        <text class="access-help-label">团队成员</text>
        <text class="access-help-value">向团队管理员获取邀请码；失效后请管理员重新生成。</text>
      </view>
    </view>

    <text class="help">邀请码失效时，请联系团队管理员重新生成。</text>
  </view>
</template>

<script setup>
import { onMounted, ref } from "vue";
import {
  ArrowRight,
  Check,
  CircleAlert,
  HelpCircle,
  KeyRound,
  LoaderCircle,
  RotateCcw,
  Server,
  ShieldCheck,
} from "@lucide/vue";
import ModuleMark from "../../components/ModuleMark.vue";
import { moduleList } from "../../data/modules";
import { bindDevice, getSession } from "../../services/session";
import { API_BASE_URL, probeService, setApiBaseUrl } from "../../services/api";

const inviteCode = ref("");
const errorMessage = ref("");
const errorIsConnection = ref(false);
const probing = ref(false);
const serviceProbe = ref(null);
const serverExpanded = ref(false);
const serverAddress = ref(API_BASE_URL);
const loading = ref(false);
const previewModules = moduleList;
const configuredInviteHint = String(import.meta.env.VITE_BOOTSTRAP_INVITE_HINT || "")
  .replace(/\D/g, "")
  .slice(0, 6);
const bootstrapInviteHint = configuredInviteHint || "246810";

async function probe() {
  if (probing.value) return serviceProbe.value;
  probing.value = true;
  try {
    serviceProbe.value = await probeService();
    serverAddress.value = serviceProbe.value.baseUrl;
    if (serviceProbe.value.ok && errorIsConnection.value) errorMessage.value = "";
    return serviceProbe.value;
  } catch (error) {
    serviceProbe.value = {
      ok: false,
      baseUrl: serverAddress.value,
      message: error.message || "服务连接检测失败",
    };
    return serviceProbe.value;
  } finally {
    probing.value = false;
  }
}

async function saveServer() {
  errorMessage.value = "";
  errorIsConnection.value = false;
  serverAddress.value = setApiBaseUrl(serverAddress.value);
  const result = await probe();
  if (!result.ok) serverExpanded.value = true;
  else serverExpanded.value = false;
}

async function retryService() {
  serverExpanded.value = true;
  const result = await probe();
  if (result.ok) uni.showToast({ title: "资料库服务已连接", icon: "success" });
}

function filterCode(event) {
  inviteCode.value = String(event.detail.value || "").replace(/\D/g, "").slice(0, 6);
}

function fillBootstrapInvite() {
  inviteCode.value = bootstrapInviteHint;
}

async function submit() {
  errorMessage.value = "";
  errorIsConnection.value = false;
  if (inviteCode.value.length !== 6 || loading.value) return;
  loading.value = true;
  try {
    await bindDevice(inviteCode.value);
    uni.reLaunch({ url: "/pages/home/index" });
  } catch (error) {
    errorMessage.value = error.message || "邀请码验证失败";
    errorIsConnection.value = error.status === 0;
    if (errorIsConnection.value) serverExpanded.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(probe);

const session = getSession();
if (session?.device_id) {
  setTimeout(() => uni.reLaunch({ url: "/pages/home/index" }), 0);
}
</script>

<style scoped>
.bind-page {
  min-height: 100vh;
  padding: 44px 22px 28px;
}
.brand-block {
  display: flex;
  flex-direction: column;
}
.brand-line {
  display: flex;
  align-items: center;
  gap: 7px;
}
.brand-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}
.brand-name {
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.13em;
}
.brand-title {
  margin-top: 26px;
  color: var(--ink);
  font-size: 33px;
  font-weight: 780;
  line-height: 43px;
}
.brand-desc {
  max-width: 320px;
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 20px;
}
.module-preview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 8px;
  margin-top: 26px;
}
.preview-item {
  min-width: 0;
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.72);
}
.preview-copy {
  min-width: 0;
}
.preview-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}
.preview-kicker {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 7px;
  letter-spacing: 0.06em;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bind-panel {
  margin-top: 22px;
  padding: 17px;
  border-radius: 12px;
  background: var(--ink);
  color: #ffffff;
  box-shadow: 0 14px 30px rgba(22, 34, 31, 0.17);
}
.panel-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.panel-icon {
  width: 40px;
  height: 40px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(169, 238, 224, 0.26);
  border-radius: 9px;
  background: rgba(129, 225, 205, 0.1);
  color: #bff4e8;
}
.panel-title {
  display: block;
  font-size: 15px;
  font-weight: 700;
}
.panel-desc {
  display: block;
  margin-top: 4px;
  color: #a9c0b9;
  font-size: 9px;
}
.code-shell {
  margin-top: 19px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.13);
  border-radius: 10px;
  background: #f8fbfa;
}
.code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.code-label {
  display: block;
  color: #52615c;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.04em;
}
.code-count {
  color: #8a9691;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}
.code-input {
  width: 100%;
  height: 54px;
  padding: 0 14px;
  border: 1px solid #cbd9d4;
  border-radius: 8px;
  background: #ffffff;
  color: #16221f;
  font-size: 23px;
  font-weight: 700;
  letter-spacing: 6px;
  text-align: center;
}
.code-progress {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 10px;
}
.progress-dot {
  width: 22px;
  height: 2px;
  border-radius: 2px;
  background: #d9e4e0;
}
.progress-dot.filled {
  background: #0b7565;
}
.service-status {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 12px;
  padding: 9px 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}
.service-icon {
  width: 30px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: rgba(213, 244, 235, 0.09);
  color: #c5eee4;
}
.service-copy {
  flex: 1;
  min-width: 0;
}
.service-title {
  display: block;
  color: #eef8f5;
  font-size: 10px;
  font-weight: 650;
}
.service-state {
  display: block;
  margin-top: 2px;
  color: #9fb4ad;
  font-size: 8px;
}
.service-state.ready {
  color: #91e2cd;
}
.service-state.failed {
  color: #f1b28d;
}
.service-action {
  flex: none;
  color: #b9d5cd;
  font-size: 9px;
}
.server-editor {
  margin-top: 8px;
  padding: 10px;
  border: 1px solid rgba(169, 238, 224, 0.16);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.045);
}
.server-input {
  width: 100%;
  height: 40px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.13);
  border-radius: 7px;
  background: rgba(0, 0, 0, 0.14);
  color: #f2fbf8;
  font-size: 10px;
}
.server-actions {
  display: flex;
  gap: 7px;
  margin-top: 8px;
}
.server-button {
  height: 32px;
  flex: 1;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: #d9e9e4;
  font-size: 9px;
  font-weight: 600;
  line-height: 30px;
}
.server-button.primary {
  border-color: transparent;
  background: #d5f4eb;
  color: #12382f;
}
.server-button[disabled] {
  opacity: 0.48;
}
.server-hint {
  display: block;
  margin-top: 7px;
  overflow-wrap: anywhere;
  color: #9fb4ad;
  font-size: 8px;
  line-height: 13px;
}
.bootstrap-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  padding: 10px 11px;
  border: 1px solid rgba(169, 238, 224, 0.16);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.055);
}
.hint-copy {
  min-width: 0;
}
.hint-label {
  display: block;
  color: #8fa8a0;
  font-size: 9px;
}
.hint-line {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-top: 3px;
}
.hint-code {
  color: #d5f4eb;
  font-size: 16px;
  font-weight: 720;
  letter-spacing: 0.12em;
  font-variant-numeric: tabular-nums;
}
.hint-desc {
  color: #9fb4ad;
  font-size: 9px;
}
.hint-fill {
  height: 32px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0 10px;
  border: 1px solid rgba(169, 238, 224, 0.21);
  border-radius: 7px;
  background: rgba(213, 244, 235, 0.09);
  color: #d5f4eb;
  font-size: 10px;
  font-weight: 650;
  line-height: 30px;
}
.error-banner {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: 10px;
  padding: 11px;
  border: 1px solid rgba(244, 177, 133, 0.32);
  border-radius: 8px;
  background: rgba(193, 92, 38, 0.18);
  color: #ffd2b6;
  line-height: 18px;
}
.bind-button {
  width: 100%;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 12px;
  border-radius: 8px;
  background: #d5f4eb;
  color: #12382f;
  font-size: 13px;
  font-weight: 700;
}
.bind-button[disabled] {
  opacity: 0.38;
}
.security-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 17px;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
}
.help {
  display: block;
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 9px;
  text-align: center;
}
.spin {
  animation: spin 900ms linear infinite;
}

.error-icon,
.service-failure svg {
  flex: none;
  margin-top: 1px;
}
.error-copy {
  min-width: 0;
  flex: 1;
}
.error-title {
  display: block;
  color: #ffe3d3;
  font-size: 12px;
  font-weight: 700;
}
.error-message {
  display: block;
  margin-top: 3px;
  overflow-wrap: anywhere;
  color: #e9b99a;
  font-size: 11px;
  line-height: 17px;
}
.error-retry,
.failure-retry {
  min-height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 0 8px;
  border: 1px solid rgba(255, 210, 182, 0.34);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.07);
  color: #ffe3d3;
  font-size: 10px;
  line-height: 28px;
}
.service-failure {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 8px;
  padding: 9px 10px;
  border: 1px solid rgba(244, 177, 133, 0.22);
  border-radius: 7px;
  background: rgba(193, 92, 38, 0.12);
  color: #f1b28d;
  font-size: 10px;
  line-height: 16px;
}
.service-failure text {
  min-width: 0;
  flex: 1;
  overflow-wrap: anywhere;
}
.access-help {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.access-help-head {
  display: flex;
  align-items: center;
  gap: 9px;
}
.access-help-icon {
  width: 34px;
  height: 34px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--accent-soft);
  color: var(--accent);
}
.access-help-title {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 700;
}
.access-help-note {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
}
.access-help-row {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.access-help-label {
  width: 58px;
  flex: none;
  color: var(--accent);
  font-size: 11px;
  font-weight: 650;
}
.access-help-value {
  min-width: 0;
  flex: 1;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 19px;
}
.bind-panel,
.preview-item,
.code-shell {
  border-radius: 8px;
}
.brand-name,
.panel-desc,
.service-title,
.service-state,
.service-action,
.server-input,
.server-button,
.server-hint,
.hint-label,
.hint-desc,
.security-note,
.help {
  font-size: 11px;
}
.preview-kicker {
  font-size: 9px;
  letter-spacing: 0;
}
@media (max-width: 360px) {
  .bind-page {
    padding-left: 16px;
    padding-right: 16px;
  }
  .brand-title {
    font-size: 30px;
    line-height: 39px;
  }
  .bind-panel {
    padding: 15px;
  }
  .code-input {
    letter-spacing: 4px;
  }
  .service-failure {
    flex-wrap: wrap;
  }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.brand-line .brand-name {
  color: var(--ink);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0;
}
.brand-suffix {
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 650;
  letter-spacing: 0;
}
</style>
