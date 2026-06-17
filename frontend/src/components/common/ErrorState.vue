<script setup lang="ts">
defineProps<{ message?: string }>()
const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="py-12 text-center">
    <p class="text-red-600 text-sm">{{ message ?? '加载失败' }}</p>
    <button
      v-if="$attrs.onRetry"
      class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
      @click="emit('retry')"
    >
      重试
    </button>
  </div>
</template>
