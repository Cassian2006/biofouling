<script setup>
defineProps({
  text: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <span class="hint-tooltip" tabindex="0" :aria-label="text">
    <span class="hint-tooltip__icon">i</span>
    <span class="hint-tooltip__bubble">{{ text }}</span>
  </span>
</template>
