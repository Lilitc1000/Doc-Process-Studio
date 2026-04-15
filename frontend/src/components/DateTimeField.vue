<template>
  <div ref="rootRef" class="date-time-picker">
    <button
      type="button"
      class="date-time-trigger"
      :class="{ open: isOpen }"
      :disabled="disabled"
      @click.stop="togglePanel"
      @keydown.esc.prevent="closePanel"
    >
      <span class="date-time-trigger-text">
        {{ displayText }}
      </span>
      <span class="date-time-trigger-icon" aria-hidden="true">
        <svg
          v-if="!isOpen"
          viewBox="0 0 20 20"
          class="date-time-trigger-icon-svg"
        >
          <rect
            x="3.25"
            y="4.5"
            width="13.5"
            height="12.25"
            rx="2.25"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          />
          <path
            d="M6.5 3.25V6M13.5 3.25V6M3.25 7.5H16.75M7.5 11L10 13.5L12.5 11"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
          />
        </svg>
        <svg v-else viewBox="0 0 20 20" class="date-time-trigger-icon-svg">
          <rect
            x="3.25"
            y="4.5"
            width="13.5"
            height="12.25"
            rx="2.25"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          />
          <path
            d="M6.5 3.25V6M13.5 3.25V6M3.25 7.5H16.75M7.5 13L10 10.5L12.5 13"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
          />
        </svg>
      </span>
    </button>

    <Teleport to="body">
      <Transition name="dropdown">
        <div
          v-if="isOpen"
          ref="panelRef"
          class="date-time-panel"
          :style="panelStyle"
          @click.stop
        >
          <div class="date-time-calendar-header">
            <button
              type="button"
              class="date-time-nav-btn"
              @click="goPrevMonth"
            >
              ‹
            </button>
            <span class="date-time-month-label">{{ monthLabel }}</span>
            <button
              type="button"
              class="date-time-nav-btn"
              @click="goNextMonth"
            >
              ›
            </button>
          </div>

          <div class="date-time-weekday-row">
            <span v-for="weekday in weekdays" :key="weekday">
              {{ weekday }}
            </span>
          </div>

          <div class="date-time-day-grid">
            <button
              v-for="day in calendarDays"
              :key="day.key"
              type="button"
              class="date-time-day-btn"
              :class="{
                muted: !day.inCurrentMonth,
                selected: isSelectedDay(day.date),
                today: isToday(day.date),
              }"
              @click="pickDay(day.date)"
            >
              {{ day.label }}
            </button>
          </div>

          <div
            class="date-time-time-row"
            :class="{ open: openTimeDropdown !== null }"
          >
            <div
              ref="hourSelectRef"
              class="date-time-time-group"
              :class="{ open: openTimeDropdown === 'hour' }"
            >
              <span>时</span>
              <div class="date-time-time-select" @click.stop>
                <button
                  type="button"
                  class="date-time-time-trigger"
                  :class="{ open: openTimeDropdown === 'hour' }"
                  :disabled="disabled"
                  @click="toggleTimeDropdown('hour')"
                  @keydown.esc.prevent="closeTimeDropdowns"
                >
                  <span class="date-time-time-trigger-text">
                    {{ selectedHour }} 时
                  </span>
                  <span class="date-time-time-trigger-icon" aria-hidden="true">
                    <svg
                      viewBox="0 0 16 16"
                      class="date-time-time-trigger-icon-svg"
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
                    v-if="openTimeDropdown === 'hour'"
                    class="date-time-time-dropdown"
                    role="listbox"
                  >
                    <button
                      v-for="hour in hourOptions"
                      :key="hour"
                      type="button"
                      class="date-time-time-option"
                      :class="{ active: selectedHour === hour }"
                      @click="selectHour(hour)"
                    >
                      {{ hour }}
                    </button>
                  </div>
                </Transition>
              </div>
            </div>
            <div
              ref="minuteSelectRef"
              class="date-time-time-group"
              :class="{ open: openTimeDropdown === 'minute' }"
            >
              <span>分</span>
              <div class="date-time-time-select" @click.stop>
                <button
                  type="button"
                  class="date-time-time-trigger"
                  :class="{ open: openTimeDropdown === 'minute' }"
                  :disabled="disabled"
                  @click="toggleTimeDropdown('minute')"
                  @keydown.esc.prevent="closeTimeDropdowns"
                >
                  <span class="date-time-time-trigger-text">
                    {{ selectedMinute }} 分
                  </span>
                  <span class="date-time-time-trigger-icon" aria-hidden="true">
                    <svg
                      viewBox="0 0 16 16"
                      class="date-time-time-trigger-icon-svg"
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
                    v-if="openTimeDropdown === 'minute'"
                    class="date-time-time-dropdown"
                    role="listbox"
                  >
                    <button
                      v-for="minute in minuteOptions"
                      :key="minute"
                      type="button"
                      class="date-time-time-option"
                      :class="{ active: selectedMinute === minute }"
                      @click="selectMinute(minute)"
                    >
                      {{ minute }}
                    </button>
                  </div>
                </Transition>
              </div>
            </div>
          </div>

          <div class="date-time-actions">
            <button
              type="button"
              class="date-time-action-btn"
              @click="clearValue"
            >
              清空
            </button>
            <button
              type="button"
              class="date-time-action-btn is-primary"
              :disabled="!pendingDate"
              @click="confirmValue"
            >
              确定
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    disabled?: boolean;
    placeholder?: string;
  }>(),
  {
    disabled: false,
    placeholder: '请选择日期和时间',
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const weekdays = ['一', '二', '三', '四', '五', '六', '日'];
const hourOptions = Array.from({ length: 24 }, (_, index) =>
  String(index).padStart(2, '0'),
);
const minuteOptions = Array.from({ length: 60 }, (_, index) =>
  String(index).padStart(2, '0'),
);

const rootRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const hourSelectRef = ref<HTMLElement | null>(null);
const minuteSelectRef = ref<HTMLElement | null>(null);
const isOpen = ref(false);
const panelStyle = ref<Record<string, string>>({});
const openTimeDropdown = ref<'hour' | 'minute' | null>(null);

const displayYear = ref(new Date().getFullYear());
const displayMonth = ref(new Date().getMonth());
const pendingDate = ref<Date | null>(null);
const selectedHour = ref('00');
const selectedMinute = ref('00');

const parseDateTimeValue = (value: string) => {
  const matched = value
    .trim()
    .match(/^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})/);
  if (!matched) {
    return null;
  }
  const [, yearText, monthText, dayText, hourText, minuteText] = matched;
  const year = Number(yearText);
  const month = Number(monthText) - 1;
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const date = new Date(year, month, day, hour, minute, 0, 0);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month ||
    date.getDate() !== day
  ) {
    return null;
  }
  return date;
};

const formatStorageValue = (value: Date) => {
  const year = String(value.getFullYear());
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  const hour = String(value.getHours()).padStart(2, '0');
  const minute = String(value.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hour}:${minute}`;
};

const formatDisplayValue = (value: Date) => {
  const year = String(value.getFullYear());
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  const hour = String(value.getHours()).padStart(2, '0');
  const minute = String(value.getMinutes()).padStart(2, '0');
  return `${year}/${month}/${day} ${hour}:${minute}`;
};

const displayText = computed(() => {
  const parsed = parseDateTimeValue(props.modelValue);
  if (!parsed) {
    return props.placeholder;
  }
  return formatDisplayValue(parsed);
});

const monthLabel = computed(() => {
  return `${displayYear.value} 年 ${displayMonth.value + 1} 月`;
});

const syncPendingStateFromModel = () => {
  const parsed = parseDateTimeValue(props.modelValue);
  const baseDate = parsed ?? new Date();
  displayYear.value = baseDate.getFullYear();
  displayMonth.value = baseDate.getMonth();
  pendingDate.value = parsed
    ? new Date(baseDate.getFullYear(), baseDate.getMonth(), baseDate.getDate())
    : null;
  selectedHour.value = String(baseDate.getHours()).padStart(2, '0');
  selectedMinute.value = String(baseDate.getMinutes()).padStart(2, '0');
};

const calendarDays = computed(() => {
  const firstDay = new Date(displayYear.value, displayMonth.value, 1);
  const firstWeekday = (firstDay.getDay() + 6) % 7;
  const gridStart = new Date(
    displayYear.value,
    displayMonth.value,
    1 - firstWeekday,
  );

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + index);
    return {
      key: `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`,
      date,
      label: String(date.getDate()),
      inCurrentMonth: date.getMonth() === displayMonth.value,
    };
  });
});

const isSameDay = (left: Date | null, right: Date | null) => {
  if (!left || !right) {
    return false;
  }
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
};

const isSelectedDay = (date: Date) => {
  return isSameDay(pendingDate.value, date);
};

const isToday = (date: Date) => {
  return isSameDay(new Date(), date);
};

const updatePanelPosition = () => {
  if (!rootRef.value) {
    return;
  }

  const triggerRect = rootRef.value.getBoundingClientRect();
  const desiredWidth = Math.max(triggerRect.width, 320);
  const margin = 10;
  const estimatedPanelHeight = 380;

  let left = triggerRect.left;
  if (left + desiredWidth + margin > window.innerWidth) {
    left = window.innerWidth - desiredWidth - margin;
  }
  if (left < margin) {
    left = margin;
  }

  let top = triggerRect.bottom + 8;
  if (
    top + estimatedPanelHeight > window.innerHeight &&
    triggerRect.top > 220
  ) {
    top = Math.max(margin, triggerRect.top - estimatedPanelHeight - 8);
  }

  panelStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${left}px`,
    width: `${desiredWidth}px`,
    zIndex: '260',
  };
};

const openPanel = async () => {
  if (props.disabled) {
    return;
  }
  syncPendingStateFromModel();
  openTimeDropdown.value = null;
  isOpen.value = true;
  await nextTick();
  updatePanelPosition();
};

const closePanel = () => {
  openTimeDropdown.value = null;
  isOpen.value = false;
};

const togglePanel = async () => {
  if (isOpen.value) {
    closePanel();
    return;
  }
  await openPanel();
};

const goPrevMonth = () => {
  if (displayMonth.value === 0) {
    displayYear.value -= 1;
    displayMonth.value = 11;
    return;
  }
  displayMonth.value -= 1;
};

const goNextMonth = () => {
  if (displayMonth.value === 11) {
    displayYear.value += 1;
    displayMonth.value = 0;
    return;
  }
  displayMonth.value += 1;
};

const pickDay = (date: Date) => {
  pendingDate.value = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
  );
  displayYear.value = date.getFullYear();
  displayMonth.value = date.getMonth();
};

const closeTimeDropdowns = () => {
  openTimeDropdown.value = null;
};

const toggleTimeDropdown = (kind: 'hour' | 'minute') => {
  if (props.disabled) {
    return;
  }
  if (openTimeDropdown.value === kind) {
    closeTimeDropdowns();
    return;
  }
  openTimeDropdown.value = kind;
};

const selectHour = (hour: string) => {
  selectedHour.value = hour;
  closeTimeDropdowns();
};

const selectMinute = (minute: string) => {
  selectedMinute.value = minute;
  closeTimeDropdowns();
};

const confirmValue = () => {
  if (!pendingDate.value) {
    return;
  }
  const combinedDate = new Date(
    pendingDate.value.getFullYear(),
    pendingDate.value.getMonth(),
    pendingDate.value.getDate(),
    Number(selectedHour.value),
    Number(selectedMinute.value),
    0,
    0,
  );
  emit('update:modelValue', formatStorageValue(combinedDate));
  closePanel();
};

const clearValue = () => {
  emit('update:modelValue', '');
  closePanel();
};

const onPointerDown = (event: Event) => {
  if (!isOpen.value) {
    return;
  }
  const targetNode = event.target as Node | null;
  if (!targetNode) {
    return;
  }
  if (
    rootRef.value?.contains(targetNode) ||
    panelRef.value?.contains(targetNode)
  ) {
    if (
      hourSelectRef.value?.contains(targetNode) ||
      minuteSelectRef.value?.contains(targetNode)
    ) {
      return;
    }
    closeTimeDropdowns();
    return;
  }
  closePanel();
};

const onEscapeDown = (event: KeyboardEvent) => {
  if (event.key !== 'Escape' || !isOpen.value) {
    return;
  }
  if (openTimeDropdown.value) {
    closeTimeDropdowns();
    return;
  }
  closePanel();
};

watch(
  () => props.modelValue,
  () => {
    if (!isOpen.value) {
      syncPendingStateFromModel();
    }
  },
);

watch(isOpen, (opened) => {
  if (opened) {
    window.addEventListener('pointerdown', onPointerDown, true);
    window.addEventListener('resize', updatePanelPosition);
    window.addEventListener('scroll', updatePanelPosition, true);
    window.addEventListener('keydown', onEscapeDown, true);
    return;
  }
  window.removeEventListener('pointerdown', onPointerDown, true);
  window.removeEventListener('resize', updatePanelPosition);
  window.removeEventListener('scroll', updatePanelPosition, true);
  window.removeEventListener('keydown', onEscapeDown, true);
});

onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', onPointerDown, true);
  window.removeEventListener('resize', updatePanelPosition);
  window.removeEventListener('scroll', updatePanelPosition, true);
  window.removeEventListener('keydown', onEscapeDown, true);
});
</script>

<style scoped src="../styles/components/date-time-field.css"></style>
