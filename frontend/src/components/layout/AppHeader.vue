<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Settings } from 'lucide-vue-next'

const router = useRouter()
</script>

<template>
  <header class="sticky top-0 z-40 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
    <h1 class="text-base font-bold text-gray-800">AI 知识库</h1>
    <button @click="router.push('/settings')" class="p-1.5 text-gray-500 hover:text-gray-700">
      <Settings :size="20" />
    </button>
  </header>
</template>
