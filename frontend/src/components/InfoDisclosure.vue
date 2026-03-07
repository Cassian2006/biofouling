<script setup>
const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  summary: {
    type: String,
    default: "",
  },
  defaultOpen: {
    type: Boolean,
    default: false,
  },
});
</script>

<template>
  <details class="info-disclosure" :open="defaultOpen">
    <summary class="info-disclosure__summary">
      <div>
        <strong>{{ title }}</strong>
        <p v-if="summary">{{ summary }}</p>
      </div>
      <span class="info-disclosure__hint">展开说明</span>
    </summary>
    <div class="info-disclosure__body">
      <slot />
    </div>
  </details>
</template>
