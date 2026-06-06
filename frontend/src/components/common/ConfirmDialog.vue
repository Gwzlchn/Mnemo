<script setup lang="ts">
defineProps<{ title: string; message: string; confirmText?: string; danger?: boolean }>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <div class="fixed inset-0 z-50 bg-gray-900/50 flex items-center justify-center p-4" @click.self="emit('cancel')">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
      <h3 class="text-lg font-bold mb-2">{{ title }}</h3>
      <p class="text-sm text-gray-600 mb-6">{{ message }}</p>
      <div class="flex gap-3 justify-end">
        <button @click="emit('cancel')" class="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
          取消
        </button>
        <button
          @click="emit('confirm')"
          class="px-4 py-2 text-sm text-white rounded-lg transition-colors"
          :class="danger ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'"
        >
          {{ confirmText ?? '确认' }}
        </button>
      </div>
    </div>
  </div>
</template>
