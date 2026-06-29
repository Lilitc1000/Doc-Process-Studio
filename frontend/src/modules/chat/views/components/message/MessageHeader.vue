<template>
  <div class="message-header">
    <div class="avatar" :class="`avatar-${role}`">
      <span class="avatar-label">{{ avatarLabel }}</span>
    </div>
    <div class="message-info">
      <span class="message-role">{{ messageRole }}</span>
      <span class="message-meta-dot" aria-hidden="true"></span>
      <span class="message-time">{{ formattedTime }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChatMessageRole } from '../../../types/chat';

const props = defineProps<{
  role: ChatMessageRole;
  timestamp: Date;
}>();

const messageRoleMap: Record<ChatMessageRole, string> = {
  user: '你',
  assistant: 'AI 助手',
  system: '系统',
};

const avatarLabelMap: Record<ChatMessageRole, string> = {
  user: 'U',
  assistant: 'AI',
  system: 'SYS',
};

const messageRole = computed(() => {
  return messageRoleMap[props.role] ?? props.role;
});

const avatarLabel = computed(() => {
  return avatarLabelMap[props.role] ?? props.role;
});

const formattedTime = computed(() => {
  return props.timestamp.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
});
</script>
