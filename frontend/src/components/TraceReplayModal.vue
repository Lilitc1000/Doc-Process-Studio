<template>
  <Teleport to="body">
    <Transition name="trace-modal-fade">
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
              <button
                type="button"
                class="trace-modal-action-btn"
                :disabled="!traceId"
                @click="$emit('copy-trace-id')"
              >
                复制 Trace ID
              </button>
              <button
                type="button"
                class="trace-modal-close-btn"
                @click="$emit('close')"
              >
                ×
              </button>
            </div>
          </header>

          <div v-if="loading" class="trace-modal-loading">
            正在加载回放详情...
          </div>
          <div v-else-if="errorMessage" class="trace-modal-error">
            <p>{{ errorMessage }}</p>
            <button
              type="button"
              class="trace-modal-retry-btn"
              @click="$emit('retry')"
            >
              重新加载
            </button>
          </div>
          <div v-else-if="payload" class="trace-modal-body">
            <section class="trace-modal-section">
              <h4>基本信息</h4>
              <ul class="trace-modal-kv-list">
                <li>会话: {{ payload.conversation_id || '-' }}</li>
                <li>聊天模型: {{ payload.model || '-' }}</li>
                <li>重排序模型: {{ payload.reranker_model || '-' }}</li>
                <li>开始时间: {{ formatDateTime(payload.started_at) }}</li>
                <li>结束状态: {{ payload.final?.done_reason || '-' }}</li>
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
                  {{ round.tool_calls_consumed ?? 0 }} 次
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
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { TraceReplayPayload } from '../types/trace';

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

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString('zh-CN', {
    hour12: false,
  });
};

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

  const errorDetail = detail.error_detail;
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
  return Boolean(detail.error || detail.error_detail);
};

const formatDetailJson = (value?: Record<string, unknown>) => {
  return JSON.stringify(value ?? {}, null, 2);
};
</script>

<style scoped src="../styles/components/trace-replay-modal.css"></style>
