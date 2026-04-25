<template>
  <div
    class="user-avatar"
    :class="[`size-${size}`]"
    :style="{ backgroundColor: color }"
  >
    {{ initial }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    username: string;
    color?: string;
    size?: 'sm' | 'md' | 'lg';
  }>(),
  {
    color: '#4f46e5',
    size: 'md',
  },
);

const initial = computed(() => {
  return props.username ? props.username.charAt(0).toUpperCase() : '?';
});
</script>

<style scoped>
.user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  font-weight: 700;
  flex-shrink: 0;
  transition: background-color 0.2s ease;
  user-select: none;
}

.user-avatar.size-sm {
  width: 28px;
  height: 28px;
  font-size: 0.72rem;
}

.user-avatar.size-md {
  width: 32px;
  height: 32px;
  font-size: 0.82rem;
}

.user-avatar.size-lg {
  width: 64px;
  height: 64px;
  font-size: 1.5rem;
}
</style>
