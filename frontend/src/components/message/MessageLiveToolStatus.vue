<template>
  <div class="message-live-tool-status" aria-live="polite">
    <div class="message-live-tool-status-leading" aria-hidden="true">
      <span class="message-live-tool-status-orbit"></span>
      <span class="message-live-tool-status-core"></span>
    </div>
    <div class="message-live-tool-status-content">
      <div class="message-live-tool-status-headline">
        <span class="message-live-tool-status-title">
          {{ liveToolStatusLabel }}
        </span>
        <span class="message-live-tool-status-phase">
          {{ liveToolStatusPhase }}
        </span>
      </div>
      <div class="message-live-tool-status-message">
        {{ status.message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChatToolStatus } from '../../types/chat';

const props = defineProps<{
  status: ChatToolStatus;
}>();

const formatFallbackToolName = (toolName?: string) => {
  const normalizedToolName = toolName?.trim() ?? '';
  if (!normalizedToolName) {
    return '';
  }
  return normalizedToolName.replaceAll('_', ' ');
};

const liveToolStatusLabel = computed(() => {
  return (
    props.status.label ||
    formatFallbackToolName(props.status.tool_name) ||
    '工具执行'
  );
});

const liveToolStatusPhase = computed(() => {
  return props.status.phase === 'finish' ? '已完成' : '进行中';
});
</script>
