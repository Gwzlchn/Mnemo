<script setup lang="ts">
defineProps<{ pct: number; animate?: boolean }>()
</script>

<template>
  <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
    <div
      class="h-full rounded-full transition-all duration-500"
      :class="animate ? 'bg-blue-500 animate-pulse' : 'bg-blue-600'"
      :style="{ width: `${Math.min(100, Math.max(0, pct))}%` }"
    />
  </div>
</template>
