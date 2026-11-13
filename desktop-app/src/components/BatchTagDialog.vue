<template>
  <el-dialog
    :model-value="modelValue"
    title="批量打标签"
    width="420px"
    @update:model-value="emit('update:modelValue', $event)"
    @open="tags = ''"
  >
    <div class="selected-count">已选择 {{ ids.length }} 条记录</div>
    <el-form label-position="top">
      <el-form-item label="标签">
        <el-input v-model="tags" maxlength="255" placeholder="多个标签用逗号分隔" />
      </el-form-item>
      <el-form-item label="处理方式">
        <el-radio-group v-model="mode">
          <el-radio value="append">追加到已有标签</el-radio>
          <el-radio value="replace">替换已有标签</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!tags.trim()" @click="submit">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../services/api";

const props = defineProps({
  modelValue: Boolean,
  module: String,
  ids: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue", "tagged"]);
const tags = ref("");
const mode = ref("append");
const saving = ref(false);

async function submit() {
  if (!tags.value.trim()) return;
  saving.value = true;
  try {
    const result = await api("/batch/tag", {
      method: "POST",
      data: { module: props.module, record_ids: props.ids, tags: tags.value.trim(), mode: mode.value },
    });
    ElMessage.success(`已更新 ${result.tagged_count} 条标签${result.denied?.length ? `，${result.denied.length} 条无权限` : ""}`);
    emit("tagged", result);
    emit("update:modelValue", false);
  } catch (error) {
    ElMessage.error(error.message || "批量打标签失败");
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.selected-count {
  margin-bottom: 12px;
  color: #666666;
  font-size: 12px;
}
</style>
