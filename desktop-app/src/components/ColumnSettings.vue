<template>
  <el-dialog
    :model-value="modelValue"
    title="列设置"
    width="520px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="column-tip">勾选总表需要展示的字段；名称列始终保留并冻结在左侧。</div>
    <el-checkbox-group v-model="localColumns" class="column-grid">
      <el-checkbox
        v-for="field in fields"
        :key="field.key"
        :value="field.key"
        :disabled="field.key === nameField"
      >
        {{ field.label }}
      </el-checkbox>
    </el-checkbox-group>
    <template #footer>
      <el-button @click="restoreDefault">恢复默认</el-button>
      <el-button type="primary" @click="save">应用</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { modules } from "../data/modules";

const props = defineProps({
  modelValue: Boolean,
  module: String,
  visibleColumns: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue", "saved"]);
const localColumns = ref([]);

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      localColumns.value = [...props.visibleColumns];
      if (!localColumns.value.includes(modules[props.module].nameField)) {
        localColumns.value.unshift(modules[props.module].nameField);
      }
    }
  },
);

function restoreDefault() {
  localColumns.value = [...modules[props.module].defaultColumns];
}

function save() {
  emit("saved", [...localColumns.value]);
  emit("update:modelValue", false);
}
</script>

<style scoped>
.column-tip {
  margin-bottom: 14px;
  color: #666666;
  font-size: 12px;
}
.column-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 24px;
}
</style>
