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
          v-if="mode === 'time'"
          viewBox="0 0 20 20"
          class="date-time-trigger-icon-svg"
        >
          <circle
            cx="10"
            cy="10"
            r="6.75"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          />
          <path
            d="M10 6.8V10.2L12.4 11.8"
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
            d="M6.5 3.25V6M13.5 3.25V6M3.25 7.5H16.75"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
          />
        </svg>
      </span>
      <span class="date-time-trigger-chevron" :class="{ open: isOpen }">
        <svg viewBox="0 0 16 16" class="date-time-trigger-chevron-svg">
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

    <teleport to="body">
      <transition name="dropdown">
        <div
          v-if="isOpen"
          ref="panelRef"
          class="date-time-panel"
          :style="panelStyle"
          @click.stop
        >
          <template v-if="mode !== 'time'">
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
          </template>

          <div
            v-if="mode !== 'date'"
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

                <transition name="dropdown">
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
                </transition>
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

                <transition name="dropdown">
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
                </transition>
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
              :disabled="confirmDisabled"
              @click="confirmValue"
            >
              确定
            </button>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

type DateTimeFieldMode = 'datetime' | 'date' | 'time';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    disabled?: boolean;
    placeholder?: string;
    mode?: DateTimeFieldMode;
  }>(),
  {
    disabled: false,
    placeholder: '请选择日期和时间',
    mode: 'datetime',
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

const mode = computed<DateTimeFieldMode>(() => props.mode ?? 'datetime');

const parseDateTimeCandidate = (value: string): Date | null => {
  const normalized = value.trim();
  const isoMatched = normalized.match(
    /^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s](\d{1,2}):(\d{1,2}))?/,
  );
  if (isoMatched) {
    const [, yearText, monthText, dayText, hourText = '00', minuteText = '00'] =
      isoMatched;
    const year = Number(yearText);
    const month = Number(monthText) - 1;
    const day = Number(dayText);
    const hour = Number(hourText);
    const minute = Number(minuteText);
    const date = new Date(year, month, day, hour, minute, 0, 0);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return date;
  }

  const slashMatched = normalized.match(
    /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:\s+(\d{1,2}):(\d{1,2}))?/,
  );
  if (slashMatched) {
    const [, dayText, monthText, yearText, hourText = '00', minuteText = '00'] =
      slashMatched;
    const year = Number(yearText);
    const month = Number(monthText) - 1;
    const day = Number(dayText);
    const hour = Number(hourText);
    const minute = Number(minuteText);
    const date = new Date(year, month, day, hour, minute, 0, 0);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return date;
  }

  return null;
};

const parseTimeCandidate = (
  value: string,
): { hour: string; minute: string } | null => {
  const normalized = value.trim();
  const applyAmpm = (rawHour: number, rawAmpm: string) => {
    let hour = rawHour;
    const ampm = rawAmpm.toLowerCase();
    if (ampm === 'pm' && hour >= 1 && hour <= 11) {
      hour += 12;
    } else if (ampm === 'am' && hour === 12) {
      hour = 0;
    }
    return hour;
  };

  const timeMatched = normalized.match(
    /(?:^|[^\d])(?<hour>\d{1,2})\s*(?:[:：时hH点])\s*(?<minute>\d{1,2})(?:\s*(?:分|m|M))?\s*(?<ampm>am|pm)?/i,
  );
  if (timeMatched?.groups) {
    const hour = applyAmpm(
      Number(timeMatched.groups.hour),
      timeMatched.groups.ampm ?? '',
    );
    const minute = Number(timeMatched.groups.minute);
    if (
      Number.isNaN(hour) ||
      Number.isNaN(minute) ||
      minute < 0 ||
      minute > 59
    ) {
      return null;
    }
    if (hour < 0 || hour > 23) {
      return null;
    }
    return {
      hour: String(hour).padStart(2, '0'),
      minute: String(minute).padStart(2, '0'),
    };
  }

  const halfMatched = normalized.match(
    /(?:^|[^\d])(?<hour>\d{1,2})\s*(?:点|时|h|H)\s*半\s*(?<ampm>am|pm)?/i,
  );
  if (halfMatched?.groups) {
    const hour = applyAmpm(
      Number(halfMatched.groups.hour),
      halfMatched.groups.ampm ?? '',
    );
    if (Number.isNaN(hour) || hour < 0 || hour > 23) {
      return null;
    }
    return {
      hour: String(hour).padStart(2, '0'),
      minute: '30',
    };
  }

  const hourOnlyMatched = normalized.match(
    /(?:^|[^\d])(?<hour>\d{1,2})\s*(?:点|时|h|H)\s*(?<ampm>am|pm)?/i,
  );
  if (!hourOnlyMatched?.groups) {
    return null;
  }
  const hour = applyAmpm(
    Number(hourOnlyMatched.groups.hour),
    hourOnlyMatched.groups.ampm ?? '',
  );
  if (Number.isNaN(hour) || hour < 0 || hour > 23) {
    return null;
  }
  return {
    hour: String(hour).padStart(2, '0'),
    minute: '00',
  };
};

const formatDateStorageValue = (value: Date) => {
  const year = String(value.getFullYear());
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const formatDateDisplayValue = (value: Date) => {
  const year = String(value.getFullYear());
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}/${month}/${day}`;
};

const formatTimeStorageValue = () => {
  return `${selectedHour.value}:${selectedMinute.value}`;
};

const formatDateTimeStorageValue = (value: Date) => {
  const year = String(value.getFullYear());
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  const hour = String(value.getHours()).padStart(2, '0');
  const minute = String(value.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hour}:${minute}`;
};

const formatDateTimeDisplayValue = (value: Date) => {
  const year = String(value.getFullYear());
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  const hour = String(value.getHours()).padStart(2, '0');
  const minute = String(value.getMinutes()).padStart(2, '0');
  return `${year}/${month}/${day} ${hour}:${minute}`;
};

const displayText = computed(() => {
  if (mode.value === 'time') {
    const parsedTime = parseTimeCandidate(props.modelValue);
    return parsedTime
      ? `${parsedTime.hour}:${parsedTime.minute}`
      : props.placeholder;
  }
  const parsedDate = parseDateTimeCandidate(props.modelValue);
  if (!parsedDate) {
    return props.placeholder;
  }
  if (mode.value === 'date') {
    return formatDateDisplayValue(parsedDate);
  }
  return formatDateTimeDisplayValue(parsedDate);
});

const monthLabel = computed(() => {
  return `${displayYear.value} 年 ${displayMonth.value + 1} 月`;
});

const syncPendingStateFromModel = () => {
  const parsed = parseDateTimeCandidate(props.modelValue);
  const parsedTime = parseTimeCandidate(props.modelValue);
  const now = new Date();
  const baseDate = parsed ?? now;
  displayYear.value = baseDate.getFullYear();
  displayMonth.value = baseDate.getMonth();
  pendingDate.value =
    mode.value === 'time'
      ? null
      : new Date(
          baseDate.getFullYear(),
          baseDate.getMonth(),
          baseDate.getDate(),
        );
  selectedHour.value =
    parsedTime?.hour ?? String(baseDate.getHours()).padStart(2, '0');
  selectedMinute.value =
    parsedTime?.minute ?? String(baseDate.getMinutes()).padStart(2, '0');
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
  const desiredWidth = Math.max(
    triggerRect.width,
    mode.value === 'time' ? 290 : 320,
  );
  const margin = 10;
  const estimatedPanelHeight =
    mode.value === 'datetime' ? 380 : mode.value === 'date' ? 330 : 220;

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

const confirmDisabled = computed(() => {
  return mode.value !== 'time' && !pendingDate.value;
});

const confirmValue = () => {
  if (mode.value === 'time') {
    emit('update:modelValue', formatTimeStorageValue());
    closePanel();
    return;
  }

  if (!pendingDate.value) {
    return;
  }

  if (mode.value === 'date') {
    emit('update:modelValue', formatDateStorageValue(pendingDate.value));
    closePanel();
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
  emit('update:modelValue', formatDateTimeStorageValue(combinedDate));
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

watch(mode, () => {
  syncPendingStateFromModel();
});

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

<style scoped>
.date-time-picker {
  position: relative;
}

.date-time-trigger {
  width: 100%;
  min-height: 44px;
  padding: 0.78rem 0.95rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.58rem;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease;
}

.date-time-trigger:hover:not(:disabled) {
  background: #f8fbff;
  border-color: #cbd5e1;
}

.date-time-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.date-time-trigger.open {
  border-color: #93c5fd;
  background: #f8fbff;
  box-shadow: 0 16px 36px rgba(59, 130, 246, 0.12);
}

.date-time-trigger-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.date-time-trigger-icon {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 999px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  transition:
    color 0.22s ease,
    background 0.22s ease,
    border-color 0.22s ease;
}

.date-time-trigger-chevron {
  width: 1.4rem;
  height: 1.4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  flex-shrink: 0;
  transition:
    transform 0.2s ease,
    color 0.2s ease;
}

.date-time-trigger-chevron.open {
  color: #1d4ed8;
  transform: rotate(180deg);
}

.date-time-trigger-chevron-svg {
  width: 0.85rem;
  height: 0.85rem;
  display: block;
}

.date-time-trigger-icon-svg {
  width: 1.08rem;
  height: 1.08rem;
  display: block;
}

.date-time-trigger.open .date-time-trigger-icon {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.date-time-panel {
  padding: 0.45rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
  box-shadow:
    0 20px 40px rgba(15, 23, 42, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.date-time-calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.45rem;
  border-radius: 12px;
  padding: 0.3rem 0.32rem 0.4rem;
  background: #f8fafc;
}

.date-time-month-label {
  font-size: 0.88rem;
  font-weight: 700;
  color: #334155;
}

.date-time-nav-btn {
  width: 1.95rem;
  height: 1.95rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  color: #475569;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    transform 0.18s ease;
}

.date-time-nav-btn:hover {
  background: #f8fafc;
  border-color: #bfdbfe;
  transform: translateY(-1px);
}

.date-time-weekday-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.22rem;
  margin-bottom: 0.18rem;
  padding-inline: 0.08rem;
}

.date-time-weekday-row span {
  text-align: center;
  font-size: 0.71rem;
  color: #64748b;
  font-weight: 600;
}

.date-time-day-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.22rem;
}

.date-time-day-btn {
  min-height: 2.05rem;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  font-size: 0.79rem;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.date-time-day-btn:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
  transform: translateY(-1px);
}

.date-time-day-btn.muted {
  color: #94a3b8;
}

.date-time-day-btn.today {
  border-color: #cbd5e1;
  background: rgba(248, 250, 252, 0.9);
}

.date-time-day-btn.selected {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 700;
  box-shadow: inset 0 0 0 1px rgba(147, 197, 253, 0.3);
}

.date-time-time-row {
  margin-top: 0.62rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  padding: 0.46rem;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fafc;
  position: relative;
  isolation: isolate;
  z-index: 2;
}

.date-time-time-row.open {
  z-index: 60;
}

.date-time-time-group {
  position: relative;
  display: grid;
  gap: 0.3rem;
  z-index: 1;
}

.date-time-time-group.open {
  z-index: 30;
}

.date-time-time-group span {
  font-size: 0.72rem;
  color: #64748b;
}

.date-time-time-select {
  position: relative;
}

.date-time-time-trigger {
  width: 100%;
  min-height: 2rem;
  border: 1px solid #dbe2ea;
  border-radius: 12px;
  padding: 0.3rem 0.5rem 0.3rem 0.58rem;
  background: #fff;
  color: #334155;
  font-size: 0.82rem;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.date-time-time-trigger:hover:not(:disabled) {
  border-color: #bfdbfe;
  background: #f8fbff;
}

.date-time-time-trigger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.date-time-time-trigger.open {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(147, 197, 253, 0.24);
  background: #f8fbff;
}

.date-time-time-trigger:focus-visible {
  outline: none;
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(147, 197, 253, 0.24);
}

.date-time-time-trigger-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.date-time-time-trigger-icon {
  width: 1.4rem;
  height: 1.4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #64748b;
  transition:
    transform 0.2s ease,
    color 0.2s ease;
}

.date-time-time-trigger-icon-svg {
  width: 0.8rem;
  height: 0.8rem;
  display: block;
}

.date-time-time-trigger.open .date-time-time-trigger-icon {
  color: #1d4ed8;
  transform: rotate(180deg);
}

.date-time-time-dropdown {
  position: absolute;
  top: calc(100% + 0.35rem);
  left: 0;
  right: 0;
  z-index: 120;
  max-height: 10.5rem;
  overflow-y: auto;
  padding: 0.32rem;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(12px);
  box-shadow:
    0 18px 36px rgba(15, 23, 42, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.date-time-time-option {
  width: 100%;
  min-height: 2rem;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #334155;
  font-size: 0.82rem;
  text-align: left;
  padding: 0.3rem 0.55rem;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.date-time-time-option:hover {
  background: #f8fafc;
  transform: translateX(2px);
}

.date-time-time-option.active {
  background: #eff6ff;
  color: #1d4ed8;
}

.date-time-actions {
  margin-top: 0.62rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.48rem;
}

.date-time-action-btn {
  min-width: 4.1rem;
  min-height: 2.05rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  color: #334155;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    transform 0.18s ease;
}

.date-time-action-btn:hover:not(:disabled) {
  border-color: #bfdbfe;
  background: #f8fafc;
  transform: translateY(-1px);
}

.date-time-action-btn.is-primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.date-time-action-btn.is-primary:hover:not(:disabled) {
  border-color: #1d4ed8;
  background: #1d4ed8;
  color: #fff;
}

.date-time-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
