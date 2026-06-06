<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'

defineProps<{ message?: string }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 text-gray-400">
    <Inbox :size="48" :stroke-width="1" />
    <p class="mt-3 text-sm">{{ message ?? '暂无数据' }}</p>
  </div>
</template>
