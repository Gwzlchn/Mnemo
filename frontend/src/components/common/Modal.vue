<script setup lang="ts">
import { X } from 'lucide-vue-next'

defineProps<{ open: boolean; title?: string }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="emit('close')"
    >
      <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 class="text-base font-bold text-gray-900">{{ title }}</h3>
          <button
            class="text-gray-500 hover:text-gray-700 transition-colors"
            aria-label="关闭"
            @click="emit('close')"
          >
            <X :size="18" />
          </button>
        </div>
        <div class="px-5 py-4">
          <slot />
        </div>
        <div v-if="$slots.footer" class="px-5 py-4 border-t border-gray-200 flex justify-end gap-3">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
