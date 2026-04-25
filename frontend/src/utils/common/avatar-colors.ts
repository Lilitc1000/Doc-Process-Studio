export const AVATAR_COLORS = [
  '#4f46e5',
  '#ef4444',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#06b6d4',
] as const;

export type AvatarColor = (typeof AVATAR_COLORS)[number];
