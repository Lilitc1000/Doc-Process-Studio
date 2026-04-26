<template>
  <div class="report-comments">
    <h3>评论</h3>
    <div class="comments-list">
      <div v-for="comment in comments" :key="comment.id" class="comment-item">
        <div class="comment-header">
          <span class="comment-author">{{ comment.author_name ?? comment.author_id }}</span>
          <span class="comment-time">{{ formatDate(comment.created_at) }}</span>
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
import type { IncidentCommentEntry } from '../../../../types/incident-report/incident-report';
import BaseTextarea from '../../../../components/base/BaseTextarea.vue';
import BaseButton from '../../../../components/base/BaseButton.vue';

const props = defineProps<{
  reportId: string;
  comments: IncidentCommentEntry[];
}>();

const emit = defineEmits<{
  (e: 'add-comment', content: string): void;
}>();

const newComment = ref('');

const formatDate = (dateStr: string) => {
  try {
    return new Date(dateStr).toLocaleString('zh-CN');
  } catch {
    return dateStr;
  }
};

const submitComment = () => {
  const content = newComment.value.trim();
  if (!content) return;
  emit('add-comment', content);
  newComment.value = '';
};
</script>

<style scoped>
.report-comments {
  margin-top: 20px;
}

.report-comments h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--color-text-primary);
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.comment-item {
  padding: 8px 12px;
  background: var(--color-bg-secondary);
  border-radius: 6px;
}

.comment-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
}

.comment-author {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.comment-time {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.comment-body {
  font-size: 13px;
  color: var(--color-text-primary);
  white-space: pre-wrap;
}

.comments-empty {
  text-align: center;
  padding: 16px;
  color: var(--color-text-tertiary);
  font-size: 13px;
}

.comment-input {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.comment-textarea {
  flex: 1;
}
</style>
