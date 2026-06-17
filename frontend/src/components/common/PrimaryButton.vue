<script setup lang="ts">
defineProps<{ disabled?: boolean; loading?: boolean }>()
const emit = defineEmits<{ click: [event: MouseEvent] }>()
</script>

<template>
  <button
    class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm"
    :disabled="disabled || loading"
    @click="emit('click', $event)"
  >
    <span
      v-if="loading"
      class="inline-block w-4 h-4 mr-2 border-2 border-white/40 border-t-white rounded-full animate-spin align-middle"
    />
    <span class="align-middle"><slot /></span>
  </button>
</template>
