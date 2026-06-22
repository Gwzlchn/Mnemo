<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { CheckCircle, XCircle, Info } from 'lucide-vue-next'

const props = defineProps<{ message: string; type?: 'success' | 'error' | 'info'; duration?: number }>()
const emit = defineEmits<{ close: [] }>()

const visible = ref(true)
let timer: ReturnType<typeof setTimeout> | null = null

watch(() => props.message, () => {
  if (timer) clearTimeout(timer)
  visible.value = true
  timer = setTimeout(() => {
    visible.value = false
    emit('close')
  }, props.duration ?? 3000)
}, { immediate: true })

onBeforeUnmount(() => { if (timer) clearTimeout(timer) })

const icons = { success: CheckCircle, error: XCircle, info: Info }
const colors = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
}
</script>

<template>
  <Transition name="toast">
    <div
      v-if="visible"
      class="fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg border shadow-lg text-sm"
      :class="colors[type ?? 'info']"
    >
      <component :is="icons[type ?? 'info']" :size="16" />
      <span>{{ message }}</span>
    </div>
  </Transition>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(-1rem); }
</style>
