<template>
  <div class="report-comments">
    <h3>评论</h3>
    <div class="comments-list">
      <div v-for="comment in comments" :key="comment.id" class="comment-item">
        <div class="comment-header">
          <span class="comment-author">{{
            comment.authorName ?? comment.authorId
          }}</span>
          <span class="comment-time">{{
            formatDateTime(comment.createdAt)
          }}</span>
        </div>
        <div class="comment-body">{{ comment.content }}</div>
      </div>
      <div v-if="comments.length === 0" class="comments-empty">暂无评论</div>
    </div>
    <div class="comment-input">
      <base-textarea
        v-model="newComment"
        placeholder="添加评论..."
        class="comment-textarea"
      />
      <base-button
        variant="primary"
        size="sm"
        :disabled="!newComment.trim()"
        @click="submitComment"
      >
        发送
      </base-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { IncidentCommentEntry } from '../../../types/incident-report';
import BaseTextarea from '@shared/ui/BaseTextarea.vue';
import BaseButton from '@shared/ui/BaseButton.vue';
import { formatDateTime } from '@shared/utils/date';

defineProps<{
  reportId: string;
  comments: IncidentCommentEntry[];
}>();

const emit = defineEmits<{
  (e: 'add-comment', content: string): void;
}>();

const newComment = ref('');

const submitComment = () => {
  const content = newComment.value.trim();
  if (!content) return;
  emit('add-comment', content);
  newComment.value = '';
};
</script>

<style scoped>
.report-comments {
  margin-top: var(--space-xl);
}

.report-comments h3 {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-md);
  color: var(--color-text-primary);
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

.comment-item {
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  transition: background var(--transition-fast);
}

.comment-item:hover {
  background: var(--color-bg-hover);
}

.comment-header {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
  margin-bottom: var(--space-xs);
}

.comment-author {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.comment-time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.comment-body {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  white-space: pre-wrap;
  line-height: var(--leading-normal);
}

.comments-empty {
  text-align: center;
  padding: var(--space-lg);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.comment-input {
  display: flex;
  gap: var(--space-sm);
  align-items: flex-end;
}

.comment-textarea {
  flex: 1;
}
</style>
