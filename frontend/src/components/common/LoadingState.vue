<script setup lang="ts">
defineProps<{ text?: string }>()
</script>

<template>
  <div class="py-12 text-center text-gray-500 text-sm">
    <span class="inline-block w-6 h-6 border-2 border-gray-200 border-t-blue-600 rounded-full animate-spin align-middle" />
    <span class="ml-2 align-middle">{{ text ?? '加载中…' }}</span>
  </div>
</template>
