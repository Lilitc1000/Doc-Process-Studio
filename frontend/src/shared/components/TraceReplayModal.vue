<template>
  <teleport to="body">
    <transition name="trace-modal-fade">
      <div v-if="visible" class="trace-modal-mask" @click.self="$emit('close')">
        <div class="trace-modal">
          <header class="trace-modal-header">
            <div class="trace-modal-title-wrap">
              <h3 class="trace-modal-title">链路回放详情</h3>
              <p v-if="traceId" class="trace-modal-trace-id">
                Trace: {{ traceId }}
              </p>
            </div>
            <div class="trace-modal-actions">
              <base-button
                type="button"
                class="trace-modal-action-btn"
                variant="secondary"
                size="sm"
                :disabled="!traceId"
                @click="$emit('copy-trace-id')"
              >
                复制 Trace ID
              </base-button>
              <base-button
                type="button"
                class="trace-modal-close-btn"
                variant="ghost"
                size="sm"
                @click="$emit('close')"
              >
                ×
              </base-button>
            </div>
          </header>

          <div v-if="loading" class="trace-modal-loading">
            正在加载回放详情...
          </div>
          <div v-else-if="errorMessage" class="trace-modal-error">
            <p>{{ errorMessage }}</p>
            <base-button
              type="button"
              class="trace-modal-retry-btn"
              variant="secondary"
              size="sm"
              @click="$emit('retry')"
            >
              重新加载
            </base-button>
          </div>
          <div v-else-if="payload" class="trace-modal-body">
            <section class="trace-modal-section">
              <h4>基本信息</h4>
              <ul class="trace-modal-kv-list">
                <li>会话: {{ payload.conversationId || '-' }}</li>
                <li>生成模型: {{ payload.model || '-' }}</li>
                <li>重排序模型: {{ payload.rerankerModel || '-' }}</li>
                <li>开始时间: {{ formatDateTime(payload.startedAt) }}</li>
                <li>结束状态: {{ payload.final?.doneReason || '-' }}</li>
                <li v-if="payload.final?.error">
                  错误: {{ payload.final.error }}
                </li>
              </ul>
            </section>

            <section v-if="payload.planner" class="trace-modal-section">
              <h4>规划器决策</h4>
              <pre class="trace-modal-code">{{
                JSON.stringify(payload.planner, null, 2)
              }}</pre>
            </section>

            <section
              v-if="payload.events && payload.events.length > 0"
              class="trace-modal-section"
            >
              <h4>关键事件</h4>
              <ul class="trace-modal-event-list">
                <li v-for="(event, index) in payload.events" :key="index">
                  <div class="trace-event-head">
                    <span
                      class="trace-event-type"
                      :class="{ 'is-error': isErrorEvent(event) }"
                    >
                      {{ event.type || '-' }}
                    </span>
                    <span class="trace-event-time">{{
                      formatDateTime(event.at)
                    }}</span>
                  </div>
                  <p
                    v-if="extractEventMessage(event)"
                    class="trace-event-message"
                  >
                    {{ extractEventMessage(event) }}
                  </p>
                  <details
                    v-if="hasEventDetail(event)"
                    class="trace-event-detail-block"
                  >
                    <summary>查看详情</summary>
                    <pre class="trace-modal-code">{{
                      formatDetailJson(event.detail)
                    }}</pre>
                  </details>
                </li>
              </ul>
            </section>

            <section
              v-if="payload.rounds && payload.rounds.length > 0"
              class="trace-modal-section"
            >
              <h4>工具轮次</h4>
              <details
                v-for="(round, index) in payload.rounds"
                :key="index"
                class="trace-round-item"
              >
                <summary>
                  第 {{ round.round ?? index + 1 }} 轮 ·
                  {{ formatDateTime(round.at) }} · 工具调用
                  {{ round.toolCallsConsumed ?? 0 }} 次
                </summary>
                <pre class="trace-modal-code">{{
                  JSON.stringify(round, null, 2)
                }}</pre>
              </details>
            </section>
          </div>
          <div v-else class="trace-modal-empty">暂未获取到链路数据。</div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import BaseButton from '../ui/BaseButton.vue';
import type { TraceReplayPayload } from '../types/trace';
import { formatDateTimeFull as formatDateTime } from '../utils/date';

defineProps<{
  visible: boolean;
  traceId: string;
  loading: boolean;
  errorMessage: string;
  payload: TraceReplayPayload | null;
}>();

defineEmits<{
  (e: 'close'): void;
  (e: 'retry'): void;
  (e: 'copy-trace-id'): void;
}>();

const hasEventDetail = (event: { detail?: Record<string, unknown> }) => {
  return Boolean(event.detail && Object.keys(event.detail).length > 0);
};

const extractEventMessage = (event: { detail?: Record<string, unknown> }) => {
  const detail = event.detail ?? {};
  const message = detail.message;
  if (typeof message === 'string' && message.trim()) {
    return message.trim();
  }

  const errorText = detail.error;
  if (typeof errorText === 'string' && errorText.trim()) {
    return errorText.trim();
  }

  const errorDetail = detail.errorDetail;
  if (
    typeof errorDetail === 'object' &&
    errorDetail !== null &&
    typeof (errorDetail as { message?: unknown }).message === 'string'
  ) {
    const nestedMessage = (errorDetail as { message: string }).message.trim();
    if (nestedMessage) {
      return nestedMessage;
    }
  }

  return '';
};

const isErrorEvent = (event: {
  type?: string;
  detail?: Record<string, unknown>;
}) => {
  if ((event.type ?? '').toLowerCase() === 'error') {
    return true;
  }
  const detail = event.detail ?? {};
  return Boolean(detail.error || detail.errorDetail);
};

const formatDetailJson = (value?: Record<string, unknown>) => {
  return JSON.stringify(value ?? {}, null, 2);
};
</script>

<style scoped>
.trace-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
  background: rgba(15, 23, 42, 0.38);
  backdrop-filter: blur(3px);
}

.trace-modal {
  width: min(880px, 100%);
  max-height: min(86vh, 920px);
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: #ffffff;
  box-shadow:
    0 26px 52px rgba(15, 23, 42, 0.28),
    0 8px 18px rgba(15, 23, 42, 0.14);
  overflow: hidden;
}

.trace-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-lg);
  padding: var(--space-lg) var(--space-xl) var(--space-lg);
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #f8fafc, #ffffff);
}

.trace-modal-title-wrap {
  min-width: 0;
}

.trace-modal-title {
  margin: 0;
  font-size: 1rem;
  line-height: 1.25;
  color: #0f172a;
}

.trace-modal-trace-id {
  margin: var(--space-xs) 0 0;
  font-size: 0.78rem;
  color: #475569;
  word-break: break-all;
}

.trace-modal-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.trace-modal-action-btn,
.base-button.trace-modal-action-btn,
.trace-modal-close-btn,
.base-button.trace-modal-close-btn,
.trace-modal-retry-btn,
.base-button.trace-modal-retry-btn {
  border: 1px solid #dbe2ea;
  background: #ffffff;
  color: #1e293b;
  border-radius: var(--radius-sm);
  min-height: 2rem;
  padding: 0 0.68rem;
  font-size: 0.8rem;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease;
}

.trace-modal-action-btn:hover:not(:disabled),
.base-button.trace-modal-action-btn:hover:not(:disabled),
.trace-modal-close-btn:hover,
.base-button.trace-modal-close-btn:hover:not(:disabled),
.trace-modal-retry-btn:hover,
.base-button.trace-modal-retry-btn:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.trace-modal-action-btn:disabled,
.base-button.trace-modal-action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.trace-modal-close-btn,
.base-button.trace-modal-close-btn {
  width: 2rem;
  min-width: 2rem;
  min-height: 2rem;
  padding: 0;
  gap: 0;
  font-size: 1rem;
  line-height: 1;
}

.trace-modal-loading,
.trace-modal-empty,
.trace-modal-error {
  padding: var(--space-lg) var(--space-xl);
  font-size: 0.88rem;
  color: #334155;
}

.trace-modal-error p {
  margin: 0 0 0.6rem;
  color: #b42318;
}

.trace-modal-body {
  overflow: auto;
  padding: var(--space-lg) var(--space-xl) var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.trace-modal-section {
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: var(--space-md) var(--space-md);
  background: #fcfdff;
}

.trace-modal-section h4 {
  margin: 0 0 0.58rem;
  font-size: 0.86rem;
  color: #0f172a;
}

.trace-modal-kv-list,
.trace-modal-event-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  font-size: 0.8rem;
  color: #334155;
}

.trace-modal-event-list li {
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-sm);
  background: #fff;
  padding: var(--space-sm) var(--space-md);
}

.trace-event-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

.trace-modal-code {
  margin: 0;
  padding: var(--space-sm) var(--space-md);
  max-height: 260px;
  overflow: auto;
  border-radius: var(--radius-sm);
  border: 1px solid #e2e8f0;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 0.74rem;
  line-height: 1.45;
}

.trace-round-item {
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-sm);
  padding: var(--space-sm) var(--space-sm);
  background: #ffffff;
}

.trace-round-item + .trace-round-item {
  margin-top: var(--space-sm);
}

.trace-round-item summary {
  cursor: pointer;
  font-size: 0.78rem;
  color: #334155;
}

.trace-round-item[open] summary {
  margin-bottom: var(--space-sm);
}

.trace-event-type {
  font-weight: 600;
  color: #0f172a;
}

.trace-event-type.is-error {
  color: #b42318;
}

.trace-event-time {
  color: #64748b;
}

.trace-event-message {
  margin: var(--space-xs) 0 0;
  color: #334155;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}

.trace-event-detail-block {
  margin-top: var(--space-sm);
}

.trace-event-detail-block summary {
  cursor: pointer;
  color: #2563eb;
  font-size: 0.78rem;
}

.trace-modal-fade-enter-active,
.trace-modal-fade-leave-active {
  transition:
    opacity 0.22s ease,
    transform 0.22s ease;
}

.trace-modal-fade-enter-from,
.trace-modal-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
