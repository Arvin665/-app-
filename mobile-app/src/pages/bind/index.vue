<template>
  <view class="bind-page app-page safe-top safe-bottom">
    <view class="brand-block">
      <view class="brand-line"><view class="brand-dot"></view><text class="brand-name">ASSET LIBRARY</text></view>
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
          <text class="panel-desc">输入 6 位邀请码，设备只需绑定一次。</text>
        </view>
      </view>

      <view class="code-shell">
        <text class="code-label">邀请码</text>
        <input
          v-model="inviteCode"
          class="code-input"
          type="number"
          maxlength="6"
          focus
          placeholder="000000"
          @input="filterCode"
          @confirm="submit"
        />
        <view class="code-progress">
          <view v-for="index in 6" :key="index" class="progress-dot" :class="{ filled: inviteCode.length >= index }"></view>
        </view>
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

    <text class="help">邀请码失效时，请联系团队管理员重新生成。</text>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { ArrowRight, KeyRound, LoaderCircle, ShieldCheck } from "@lucide/vue";
import ModuleMark from "../../components/ModuleMark.vue";
import { moduleList } from "../../data/modules";
import { bindDevice, getSession } from "../../services/session";

const inviteCode = ref("");
const loading = ref(false);
const previewModules = moduleList;

function filterCode(event) {
  inviteCode.value = String(event.detail.value || "").replace(/\D/g, "").slice(0, 6);
}

async function submit() {
  if (inviteCode.value.length !== 6 || loading.value) return;
  loading.value = true;
  try {
    await bindDevice(inviteCode.value);
    uni.reLaunch({ url: "/pages/home/index" });
  } catch (error) {
    uni.showToast({ title: error.message || "邀请码验证失败", icon: "none", duration: 2600 });
  } finally {
    loading.value = false;
  }
}

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
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 26px;
}
.preview-item {
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
  padding: 12px 13px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.06);
}
.code-label {
  display: block;
  color: #a9c0b9;
  font-size: 8px;
  font-weight: 650;
  letter-spacing: 0.08em;
}
.code-input {
  width: 100%;
  height: 52px;
  color: #ffffff;
  font-size: 31px;
  font-weight: 700;
  letter-spacing: 8px;
  text-align: center;
}
.code-progress {
  display: flex;
  justify-content: center;
  gap: 6px;
}
.progress-dot {
  width: 22px;
  height: 2px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.13);
}
.progress-dot.filled {
  background: #8ee0cc;
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
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
