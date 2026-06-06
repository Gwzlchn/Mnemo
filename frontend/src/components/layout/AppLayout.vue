<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import AppBottomNav from './AppBottomNav.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col md:flex-row">
    <AppSidebar class="hidden md:flex" />
    <div class="flex-1 flex flex-col min-w-0">
      <AppHeader class="md:hidden" />
      <main class="flex-1 p-4 pb-20 md:pb-4 md:p-6 max-w-5xl w-full mx-auto">
        <slot />
      </main>
      <AppBottomNav class="md:hidden" />
    </div>
  </div>
</template>
