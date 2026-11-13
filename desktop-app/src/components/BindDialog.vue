<template>
  <el-dialog
    :model-value="true"
    width="420px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    title="设备绑定"
  >
    <div class="bind-copy">
      <strong>商办信息资产库</strong>
      <span>输入团队邀请码，绑定后无需重复登录。</span>
    </div>
    <el-form label-position="top" @submit.prevent>
      <el-form-item label="6 位数字邀请码">
        <el-input
          v-model="inviteCode"
          maxlength="6"
          size="large"
          placeholder="请输入邀请码"
          inputmode="numeric"
          @input="inviteCode = inviteCode.replace(/\\D/g, '').slice(0, 6)"
          @keyup.enter="submit"
        />
      </el-form-item>
    </el-form>
    <div class="device-line">当前设备：{{ deviceName }}</div>
    <template #footer>
      <el-button type="primary" :loading="loading" :disabled="inviteCode.length !== 6" @click="submit">
        验证并进入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../services/api";
import { getDeviceId, getDeviceName, saveSession } from "../services/device";

const emit = defineEmits(["bound"]);
const inviteCode = ref("");
const loading = ref(false);
const deviceName = getDeviceName();

async function submit() {
  if (inviteCode.value.length !== 6 || loading.value) return;
  loading.value = true;
  try {
    const session = await api("/auth/bind", {
      method: "POST",
      data: { invite_code: inviteCode.value, device_id: getDeviceId(), device_name: deviceName },
    });
    saveSession(session);
    emit("bound", session);
  } catch (error) {
    ElMessage.error(error.message || "邀请码验证失败");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.bind-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 18px;
}
.bind-copy strong {
  font-size: 20px;
  font-weight: 600;
}
.bind-copy span,
.device-line {
  color: #666;
  font-size: 12px;
}
.device-line {
  margin-top: 4px;
}
</style>
