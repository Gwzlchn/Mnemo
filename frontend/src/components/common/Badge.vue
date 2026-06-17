<script setup lang="ts">
import { computed } from 'vue'

type Variant = 'default' | 'success' | 'warn' | 'info'

const props = defineProps<{ variant?: Variant }>()

const variantClass = computed(() => {
  const map: Record<Variant, string> = {
    default: 'bg-gray-100 text-gray-600',
    success: 'bg-green-100 text-green-700',
    warn: 'bg-amber-100 text-amber-700',
    info: 'bg-blue-100 text-blue-700',
  }
  return map[props.variant ?? 'default']
})
</script>

<template>
  <span
    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
    :class="variantClass"
  >
    <slot />
  </span>
</template>
