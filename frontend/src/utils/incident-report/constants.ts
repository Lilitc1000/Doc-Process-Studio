const STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED = 'follow_up_action_required';
const STATUS_OPTION_CLOSED = 'closed';

export const statusOptions = [
  { value: STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED, label: '跟进中' },
  { value: STATUS_OPTION_CLOSED, label: '已关闭' },
];

const SEVERITY_OPTION_P0 = 'P0';
const SEVERITY_OPTION_P1 = 'P1';
const SEVERITY_OPTION_P2 = 'P2';
const SEVERITY_OPTION_P3 = 'P3';

export const severityOptions = [
  { value: SEVERITY_OPTION_P0, label: 'P0 - 紧急' },
  { value: SEVERITY_OPTION_P1, label: 'P1 - 严重' },
  { value: SEVERITY_OPTION_P2, label: 'P2 - 一般' },
  { value: SEVERITY_OPTION_P3, label: 'P3 - 轻微' },
];
