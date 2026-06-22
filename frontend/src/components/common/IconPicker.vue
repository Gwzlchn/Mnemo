<script setup lang="ts">
// 知识库图标选择网格(v-model:icon)。HomeView 新建弹窗与 ProfileEditor 共用,
// 替代两处逐字重复的 icon-grid 标记。
import { resolveIcon, ICON_NAMES } from '../../utils/kbIcons'
import { Lightbulb } from 'lucide-vue-next'

defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()
</script>

<template>
  <div class="icon-grid">
    <button
      v-for="name in ICON_NAMES" :key="name" type="button" class="icon-pick"
      :class="{ on: modelValue === name }" @click="emit('update:modelValue', name)"
    >
      <component :is="resolveIcon(name) || Lightbulb" :size="18" />
    </button>
  </div>
</template>
