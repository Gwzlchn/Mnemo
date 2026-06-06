<script setup lang="ts">
defineProps<{
  headings: { id: string; text: string; level: number }[]
}>()

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <nav v-if="headings.length > 0" class="space-y-1">
    <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">目录</h4>
    <a
      v-for="h in headings"
      :key="h.id"
      @click.prevent="scrollTo(h.id)"
      class="block text-sm text-gray-600 hover:text-blue-600 cursor-pointer truncate transition-colors"
      :class="h.level === 3 ? 'pl-4' : ''"
    >
      {{ h.text }}
    </a>
  </nav>
</template>
