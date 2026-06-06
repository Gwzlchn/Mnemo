<script setup lang="ts">
import { computed } from 'vue'
import type { StepInfo } from '../../types'
import { Check, X, Minus, Loader } from 'lucide-vue-next'

const props = defineProps<{ steps: StepInfo[] }>()

const statusIcon: Record<string, any> = {
  done: Check,
  failed: X,
  skipped: Minus,
  running: Loader,
}

const statusColor: Record<string, string> = {
  done: 'bg-green-500 text-white',
  failed: 'bg-red-500 text-white',
  running: 'bg-blue-500 text-white animate-pulse',
  skipped: 'bg-gray-300 text-gray-500',
  waiting: 'bg-gray-200 text-gray-400',
  ready: 'bg-yellow-400 text-white',
}

const lineColor: Record<string, string> = {
  done: 'bg-green-500',
  failed: 'bg-red-500',
  running: 'bg-blue-500',
  skipped: 'bg-gray-300',
}

function stepPct(step: StepInfo): number | null {
  if (step.status === 'running' && step.meta?.pct != null) return step.meta.pct
  return null
}

function stepLabel(name: string): string {
  return name.replace(/^\d+[a-z]?_/, '')
}

function formatDuration(sec: number | null): string {
  if (sec == null) return ''
  if (sec < 60) return `${sec.toFixed(1)}s`
  return `${Math.floor(sec / 60)}m${Math.floor(sec % 60)}s`
}
</script>

<template>
  <!-- Mobile: vertical timeline -->
  <div class="md:hidden space-y-0">
    <div v-for="(step, idx) in steps" :key="step.name" class="flex gap-3">
      <div class="flex flex-col items-center">
        <div
          class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
          :class="statusColor[step.status] || statusColor.waiting"
        >
          <component :is="statusIcon[step.status]" v-if="statusIcon[step.status]" :size="14" />
          <span v-else class="text-xs">{{ idx + 1 }}</span>
        </div>
        <div v-if="idx < steps.length - 1" class="w-0.5 h-8 -my-0.5" :class="lineColor[step.status] || 'bg-gray-200'" />
      </div>
      <div class="pb-6 min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium" :class="step.status === 'waiting' ? 'text-gray-400' : 'text-gray-800'">
            {{ stepLabel(step.name) }}
          </span>
          <span v-if="step.duration_sec" class="text-xs text-gray-400">{{ formatDuration(step.duration_sec) }}</span>
        </div>
        <div v-if="stepPct(step) != null" class="mt-1 w-full bg-gray-200 rounded-full h-1.5">
          <div class="bg-blue-500 h-full rounded-full transition-all" :style="{ width: `${stepPct(step)}%` }" />
        </div>
        <p v-if="step.error" class="text-xs text-red-600 mt-1 truncate">{{ step.error }}</p>
      </div>
    </div>
  </div>

  <!-- Desktop: horizontal pipeline -->
  <div class="hidden md:flex items-center gap-1 overflow-x-auto pb-2">
    <template v-for="(step, idx) in steps" :key="step.name">
      <div class="flex flex-col items-center flex-shrink-0 group relative">
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center"
          :class="statusColor[step.status] || statusColor.waiting"
        >
          <component :is="statusIcon[step.status]" v-if="statusIcon[step.status]" :size="14" />
          <span v-else class="text-xs">{{ idx + 1 }}</span>
        </div>
        <span class="text-xs mt-1 text-gray-500 max-w-[60px] truncate text-center">{{ stepLabel(step.name) }}</span>
        <span v-if="step.duration_sec" class="text-xs text-gray-400">{{ formatDuration(step.duration_sec) }}</span>
        <!-- Tooltip -->
        <div class="absolute bottom-full mb-2 hidden group-hover:block bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
          {{ step.name }} - {{ step.status }}
          <span v-if="step.error"> - {{ step.error }}</span>
        </div>
      </div>
      <div v-if="idx < steps.length - 1" class="w-6 h-0.5 flex-shrink-0" :class="lineColor[step.status] || 'bg-gray-200'" />
    </template>
  </div>
</template>
