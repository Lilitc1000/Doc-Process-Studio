<template>
  <div class="incident-workspace">
    <Transition name="session-switch" mode="out-in">
      <section v-if="!session" key="welcome" class="incident-welcome">
        <h2>事故报告助手</h2>
        <p class="incident-welcome-text">
          {{
            schema?.introMessage ||
            '欢迎使用事故报告专区。这里可以引导你整理事故信息，并生成标准化附件。'
          }}
        </p>
        <ul class="incident-welcome-list">
          <li>统一填写事故关键字段，避免漏项。</li>
          <li>生成前自动校验必填项并提示缺失位置。</li>
          <li>支持链路回放，追踪生成过程与回退状态。</li>
        </ul>
        <button
          type="button"
          class="incident-primary-btn"
          @click="$emit('start')"
        >
          开始
        </button>
      </section>

      <section v-else key="form" class="incident-form-page">
        <header class="incident-form-header">
          <h2>{{ session.title }}</h2>
          <span class="incident-status">{{ statusLabel }}</span>
        </header>

        <p v-if="session.snapshot.fallbackUsed" class="incident-fallback-hint">
          LLM
          润色失败，已回退为原始表单数据生成。你可以在链路回放中查看详细状态。
        </p>

        <div class="incident-form-list">
          <div
            v-for="step in schema?.steps ?? []"
            :key="step.id"
            class="incident-form-item"
            :class="{
              invalid: missingStepIdSet.has(step.id),
              'select-open':
                step.kind === 'single_select' && openSingleSelectId === step.id,
            }"
          >
            <label class="incident-form-label">
              <span>{{ step.title }}</span>
              <span v-if="step.required" class="required-star">*</span>
            </label>
            <p class="incident-form-prompt">{{ step.prompt }}</p>

            <textarea
              v-if="step.kind === 'text' && !isDateStep(step.id)"
              :value="getTextValue(step.id)"
              :placeholder="step.placeholder || '请输入内容'"
              :disabled="isFormLocked"
              rows="3"
              @input="
                onTextInput(
                  step.id,
                  ($event.target as HTMLTextAreaElement).value,
                )
              "
            ></textarea>

            <DateTimeField
              v-else-if="step.kind === 'text' && isDateStep(step.id)"
              :model-value="getTextValue(step.id)"
              :disabled="isFormLocked"
              :placeholder="step.placeholder || '请选择日期和时间'"
              @update:model-value="onTextInput(step.id, $event)"
            />

            <div
              v-else-if="step.kind === 'single_select'"
              class="incident-single-select"
            >
              <div class="incident-select" @click.stop>
                <button
                  type="button"
                  class="incident-select-trigger"
                  :class="{ open: openSingleSelectId === step.id }"
                  :disabled="isFormLocked"
                  @click="toggleSingleSelectDropdown(step.id)"
                  @keydown.esc.prevent="closeSingleSelectDropdown"
                >
                  <span class="incident-select-trigger-text">
                    {{ getSingleSelectLabel(step) }}
                  </span>
                  <span class="incident-select-trigger-icon" aria-hidden="true">
                    <svg
                      viewBox="0 0 16 16"
                      class="incident-select-trigger-icon-svg"
                    >
                      <path
                        d="M3.5 6.25L8 10.75L12.5 6.25"
                        fill="none"
                        stroke="currentColor"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                      />
                    </svg>
                  </span>
                </button>

                <Transition name="dropdown">
                  <div
                    v-if="openSingleSelectId === step.id"
                    class="incident-select-dropdown"
                    role="listbox"
                  >
                    <button
                      type="button"
                      class="incident-select-option"
                      :class="{ active: getSingleValue(step.id) === '' }"
                      @click="onSingleSelectOption(step.id, '')"
                    >
                      请选择
                    </button>
                    <button
                      v-for="option in step.options"
                      :key="option.value"
                      type="button"
                      class="incident-select-option"
                      :class="{
                        active: getSingleValue(step.id) === option.value,
                      }"
                      @click="onSingleSelectOption(step.id, option.value)"
                    >
                      {{ option.label }}
                    </button>
                  </div>
                </Transition>
              </div>
              <input
                v-if="step.allowCustom"
                type="text"
                :value="getCustomValue(step.id)"
                :placeholder="step.placeholder || '可输入自定义内容'"
                :disabled="isFormLocked"
                @input="
                  onCustomInput(
                    step.id,
                    ($event.target as HTMLInputElement).value,
                  )
                "
              />
            </div>

            <div v-else class="incident-multi-select">
              <label
                v-for="option in step.options"
                :key="option.value"
                class="incident-checkbox-item"
              >
                <input
                  type="checkbox"
                  :checked="getMultiValues(step.id).includes(option.value)"
                  :disabled="isFormLocked"
                  @change="
                    onMultiSelectChange(
                      step.id,
                      option.value,
                      ($event.target as HTMLInputElement).checked,
                    )
                  "
                />
                <span>{{ option.label }}</span>
              </label>
              <input
                v-if="step.allowCustom"
                type="text"
                :value="getCustomValue(step.id)"
                :placeholder="step.placeholder || '可输入自定义内容'"
                :disabled="isFormLocked"
                @input="
                  onCustomInput(
                    step.id,
                    ($event.target as HTMLInputElement).value,
                  )
                "
              />
            </div>

            <p v-if="missingStepIdSet.has(step.id)" class="incident-error-text">
              此项为必填，请补充后再生成附件。
            </p>
          </div>
        </div>

        <footer class="incident-form-actions">
          <button
            type="button"
            class="incident-primary-btn"
            :disabled="isGenerating"
            @click="onGenerateOrDownload"
          >
            {{ generateButtonLabel }}
          </button>
          <button
            v-if="session.snapshot.generatedTraceId"
            type="button"
            class="incident-secondary-btn"
            :disabled="isGenerating"
            @click="$emit('open-trace', session.snapshot.generatedTraceId)"
          >
            链路回放
          </button>
        </footer>
      </section>
    </Transition>

    <Teleport to="body">
      <Transition name="dialog-fade">
        <div v-if="generationState !== 'idle'" class="incident-modal-mask">
          <div class="incident-modal">
            <p
              v-if="generationState === 'generating'"
              class="incident-modal-line"
            >
              <span class="incident-modal-icon spinning" aria-hidden="true">
                <svg viewBox="0 0 20 20" class="incident-modal-icon-svg">
                  <circle
                    cx="10"
                    cy="10"
                    r="7"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-dasharray="30 18"
                  />
                </svg>
              </span>
              <span>正在生成中，请稍候</span>
            </p>
            <template v-if="generationState === 'generating'">
              <ul
                v-if="generationProgressLines.length > 0"
                class="incident-modal-progress"
              >
                <li
                  v-for="(line, index) in generationProgressLines"
                  :key="`progress-${index}`"
                >
                  {{ line }}
                </li>
              </ul>
              <div class="incident-modal-actions">
                <button
                  type="button"
                  class="incident-secondary-btn"
                  @click="$emit('stop-generation')"
                >
                  停止生成
                </button>
              </div>
            </template>
            <template v-else>
              <p class="incident-modal-line">
                <span class="incident-modal-icon" aria-hidden="true">
                  <svg viewBox="0 0 20 20" class="incident-modal-icon-svg">
                    <path
                      d="M10 3.5V11.5M7.2 8.8L10 11.6L12.8 8.8M4.5 13.2V15.5H15.5V13.2"
                      fill="none"
                      stroke="currentColor"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="1.8"
                    />
                  </svg>
                </span>
                <span>附件已生成，请下载</span>
              </p>
              <button
                type="button"
                class="incident-secondary-btn"
                @click="$emit('close-notice')"
              >
                我知道了
              </button>
            </template>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import DateTimeField from './DateTimeField.vue';
import type {
  IncidentFormAnswer,
  IncidentFormStep,
  IncidentFormSchemaPayload,
  IncidentSessionDetail,
} from '../types/incident-report';

const props = defineProps<{
  schema: IncidentFormSchemaPayload | null;
  session: IncidentSessionDetail | null;
  isGenerating: boolean;
  generationState: 'idle' | 'generating' | 'done';
  generationTraceId?: string | null;
  generationProgressLines?: string[];
}>();

const emit = defineEmits<{
  (e: 'start'): void;
  (e: 'update-answers', answers: Record<string, IncidentFormAnswer>): void;
  (e: 'generate'): void;
  (e: 'stop-generation'): void;
  (e: 'download'): void;
  (e: 'open-trace', traceId: string): void;
  (e: 'close-notice'): void;
}>();

const localAnswers = ref<Record<string, IncidentFormAnswer>>({});
const missingStepIds = ref<string[]>([]);
const openSingleSelectId = ref<string | null>(null);

watch(
  () => props.session?.snapshot.formAnswers,
  (nextAnswers) => {
    localAnswers.value = JSON.parse(
      JSON.stringify(nextAnswers ?? {}),
    ) as Record<string, IncidentFormAnswer>;
    missingStepIds.value = [];
  },
  { immediate: true },
);

watch(
  () => props.session?.id,
  () => {
    openSingleSelectId.value = null;
  },
  { immediate: true },
);

const closeSingleSelectDropdown = () => {
  openSingleSelectId.value = null;
};

const handleWindowClick = () => {
  closeSingleSelectDropdown();
};

onMounted(() => {
  window.addEventListener('click', handleWindowClick);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', handleWindowClick);
});

const missingStepIdSet = computed(() => new Set(missingStepIds.value));

const isFormLocked = computed(() => {
  return props.isGenerating || Boolean(props.session?.snapshot.isLocked);
});

const statusLabel = computed(() => {
  const status = props.session?.status ?? 'draft';
  if (status === 'generated') {
    return '已生成';
  }
  if (status === 'generating') {
    return '生成中';
  }
  if (status === 'failed') {
    return '生成失败';
  }
  return '未生成';
});

const generateButtonLabel = computed(() => {
  if (props.session?.snapshot.generatedAttachment) {
    return '下载附件';
  }
  return '生成附件';
});

const isDateStep = (stepId: string) => {
  return ['start_time', 'detected_time', 'resolved_time'].includes(stepId);
};

const ensureAnswer = (stepId: string) => {
  if (!localAnswers.value[stepId]) {
    localAnswers.value[stepId] = {
      value: '',
      customValue: '',
    };
  }
  return localAnswers.value[stepId];
};

const emitAnswerUpdate = () => {
  emit('update-answers', JSON.parse(JSON.stringify(localAnswers.value)));
};

const getTextValue = (stepId: string) => {
  const answer = localAnswers.value[stepId];
  return typeof answer?.value === 'string' ? answer.value : '';
};

const getSingleValue = (stepId: string) => {
  const answer = localAnswers.value[stepId];
  return typeof answer?.value === 'string' ? answer.value : '';
};

const getCustomValue = (stepId: string) => {
  return localAnswers.value[stepId]?.customValue ?? '';
};

const getMultiValues = (stepId: string) => {
  const answer = localAnswers.value[stepId];
  return Array.isArray(answer?.value) ? answer.value : [];
};

const onTextInput = (stepId: string, value: string) => {
  const answer = ensureAnswer(stepId);
  answer.value = value;
  emitAnswerUpdate();
};

const onSingleSelect = (stepId: string, value: string) => {
  const answer = ensureAnswer(stepId);
  answer.value = value;
  emitAnswerUpdate();
};

const toggleSingleSelectDropdown = (stepId: string) => {
  if (isFormLocked.value) {
    return;
  }
  if (openSingleSelectId.value === stepId) {
    openSingleSelectId.value = null;
    return;
  }
  openSingleSelectId.value = stepId;
};

const onSingleSelectOption = (stepId: string, value: string) => {
  onSingleSelect(stepId, value);
  closeSingleSelectDropdown();
};

const getSingleSelectLabel = (step: IncidentFormStep) => {
  const selectedValue = getSingleValue(step.id);
  if (!selectedValue) {
    return '请选择';
  }
  const matchedOption = step.options.find(
    (option) => option.value === selectedValue,
  );
  return matchedOption?.label || selectedValue;
};

const onCustomInput = (stepId: string, value: string) => {
  const answer = ensureAnswer(stepId);
  answer.customValue = value;
  emitAnswerUpdate();
};

const onMultiSelectChange = (
  stepId: string,
  value: string,
  checked: boolean,
) => {
  const answer = ensureAnswer(stepId);
  const currentValues = Array.isArray(answer.value)
    ? [...new Set(answer.value)]
    : [];

  if (checked) {
    if (!currentValues.includes(value)) {
      currentValues.push(value);
    }
  } else {
    answer.value = currentValues.filter((item) => item !== value);
    emitAnswerUpdate();
    return;
  }

  answer.value = currentValues;
  emitAnswerUpdate();
};

const validateRequiredFields = () => {
  const steps = props.schema?.steps ?? [];
  const missing: string[] = [];

  for (const step of steps) {
    if (!step.required) {
      continue;
    }

    const answer = localAnswers.value[step.id];
    const customValue = (answer?.customValue ?? '').trim();

    if (step.kind === 'text' || step.kind === 'single_select') {
      const value =
        typeof answer?.value === 'string' ? answer.value.trim() : '';
      if (!value && !customValue) {
        missing.push(step.id);
      }
      continue;
    }

    const valueList = Array.isArray(answer?.value)
      ? answer.value.filter((item) => item.trim().length > 0)
      : [];
    if (valueList.length === 0 && !customValue) {
      missing.push(step.id);
    }
  }

  missingStepIds.value = missing;
  return missing.length === 0;
};

const onGenerateOrDownload = () => {
  if (!props.session) {
    return;
  }
  if (props.session.snapshot.generatedAttachment) {
    emit('download');
    return;
  }
  if (!validateRequiredFields()) {
    return;
  }
  emit('generate');
};

const generationProgressLines = computed(() => {
  return props.generationProgressLines ?? [];
});
</script>

<style scoped src="../styles/components/incident-report-workspace.css"></style>
