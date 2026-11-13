<template>
  <view class="bind-page safe-top safe-bottom">
    <view class="brand-block">
      <text class="brand">商办信息资产库</text>
      <text class="welcome">输入团队邀请码，绑定后无需重复登录</text>
    </view>

    <view class="bind-card">
      <text class="label">6 位数字邀请码</text>
      <input
        v-model="inviteCode"
        class="code-input"
        type="number"
        maxlength="6"
        focus
        placeholder="请输入邀请码"
        @input="filterCode"
        @confirm="submit"
      />
      <text class="device-note">当前设备将与此邀请码绑定</text>
      <button class="primary-button submit" :disabled="loading || inviteCode.length !== 6" @tap="submit">
        {{ loading ? "绑定中..." : "验证并进入" }}
      </button>
    </view>

    <text class="help">如邀请码失效，请联系团队管理员重新生成。</text>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { bindDevice, getSession } from "../../services/session";

const inviteCode = ref("");
const loading = ref(false);

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
    uni.showToast({ title: error.message || "邀请码验证失败", icon: "none" });
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
  padding: 72px 24px 24px;
  background: var(--page-bg);
}
.brand-block {
  display: flex;
  flex-direction: column;
}
.brand {
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 0;
}
.welcome {
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 22px;
}
.bind-card {
  margin-top: 48px;
  padding: 24px;
  border-radius: 8px;
  background: var(--surface);
}
.label {
  display: block;
  margin-bottom: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}
.code-input {
  width: 100%;
  height: 56px;
  border-bottom: 1px solid var(--border);
  color: var(--text-primary);
  font-size: 30px;
  font-weight: 600;
  letter-spacing: 8px;
  text-align: center;
}
.device-note {
  display: block;
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}
.submit {
  width: 100%;
  margin-top: 24px;
}
.submit[disabled] {
  opacity: 0.45;
}
.help {
  display: block;
  margin-top: 20px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 20px;
  text-align: center;
}
</style>
