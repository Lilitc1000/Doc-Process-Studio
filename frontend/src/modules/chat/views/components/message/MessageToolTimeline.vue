<template>
  <details
    v-if="showToolStatuses"
    class="message-tool-status"
    :open="isToolStatusPanelOpen"
    :class="{ 'is-processing': isToolStatusPanelOpen }"
  >
    <summary class="message-tool-status-summary">
      <span class="message-tool-status-title">
        {{ isToolStatusPanelOpen ? '处理中' : '处理过程' }}
      </span>
      <span class="message-tool-status-count"
        >{{ toolStatuses.length }} 条</span
      >
    </summary>
    <div class="message-tool-status-list">
      <div
        v-for="toolStatus in toolStatuses"
        :key="toolStatus.id"
        class="message-tool-status-item"
        :class="{
          'is-running': toolStatus.phase === 'start',
          'is-finished': toolStatus.phase === 'finish',
        }"
      >
        <span class="message-tool-status-dot" aria-hidden="true"></span>
        <div class="message-tool-status-body">
          <div class="message-tool-status-headline">
            <span class="message-tool-status-message">
              {{ toolStatus.message }}
            </span>
            <span
              class="message-tool-status-phase"
              :class="{
                'is-running': toolStatus.phase === 'start',
                'is-finished': toolStatus.phase === 'finish',
              }"
            >
              {{ formatToolPhase(toolStatus.phase) }}
            </span>
          </div>
          <span
            v-if="
              toolStatus.label || toolStatus.toolName || toolStatus.createdAt
            "
            class="message-tool-status-meta"
          >
            <template v-if="toolStatus.label || toolStatus.toolName">
              {{
                toolStatus.label || formatFallbackToolName(toolStatus.toolName)
              }}
            </template>
            <template
              v-if="
                (toolStatus.label || toolStatus.toolName) &&
                toolStatus.createdAt
              "
            >
              <span class="message-tool-status-separator">·</span>
            </template>
            <template v-if="toolStatus.createdAt">
              {{ formatStatusTime(toolStatus.createdAt) }}
            </template>
          </span>
        </div>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChatToolStatus } from '../../../types/chat';

const props = defineProps<{
  toolStatuses: ChatToolStatus[];
  isStreaming?: boolean;
}>();

const hasRunningToolStatus = computed(() => {
  if (!(props.isStreaming ?? false)) {
    return false;
  }
  const lastToolStatus = props.toolStatuses[props.toolStatuses.length - 1];
  return lastToolStatus?.phase === 'start';
});

const isToolStatusPanelOpen = computed(() => {
  return (props.isStreaming ?? false) || hasRunningToolStatus.value;
});

const showToolStatuses = computed(() => {
  return props.toolStatuses.length > 0 && !(props.isStreaming ?? false);
});

const formatStatusTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

const formatToolPhase = (phase?: string) => {
  if (phase === 'start') {
    return '进行中';
  }
  if (phase === 'finish') {
    return '已完成';
  }
  return '处理中';
};

const formatFallbackToolName = (toolName?: string) => {
  const normalizedToolName = toolName?.trim() ?? '';
  if (!normalizedToolName) {
    return '';
  }
  return normalizedToolName.replaceAll('_', ' ');
};
</script>
