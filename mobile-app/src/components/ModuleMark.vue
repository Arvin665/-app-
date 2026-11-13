<template>
  <view class="module-mark" :class="[`tone-${moduleKey}`, `size-${size}`]">
    <component :is="icon" :size="iconSize" :stroke-width="1.9" />
  </view>
</template>

<script setup>
import { computed } from "vue";
import { BriefcaseBusiness, Building2, ClipboardCheck, Sparkles } from "@lucide/vue";

const props = defineProps({
  moduleKey: { type: String, default: "sale" },
  size: { type: String, default: "md" },
});

const icons = {
  sale: Building2,
  lease: BriefcaseBusiness,
  work: ClipboardCheck,
  inspiration: Sparkles,
};
const icon = computed(() => icons[props.moduleKey] || Building2);
const iconSize = computed(() => ({ sm: 16, md: 21, lg: 28 }[props.size] || 21));
</script>

<style scoped>
.module-mark {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}
.size-sm {
  width: 30px;
  height: 30px;
}
.size-md {
  width: 42px;
  height: 42px;
}
.size-lg {
  width: 56px;
  height: 56px;
}
.tone-sale {
  background: var(--sale-soft);
  color: var(--sale);
}
.tone-lease {
  background: var(--lease-soft);
  color: var(--lease);
}
.tone-work {
  background: var(--work-soft);
  color: var(--work);
}
.tone-inspiration {
  background: var(--inspiration-soft);
  color: var(--inspiration);
}
</style>
