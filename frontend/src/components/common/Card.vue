<script setup lang="ts">
defineProps<{ padding?: string }>()
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-xl" :class="padding ?? 'p-4'">
    <slot />
  </div>
</template>
