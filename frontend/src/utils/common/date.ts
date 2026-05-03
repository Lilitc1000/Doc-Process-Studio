export function formatDate(
  value: string | null | undefined,
  fallback = '-',
): string {
  if (!value) return fallback;
  try {
    return new Date(value).toLocaleDateString('zh-CN');
  } catch {
    return value;
  }
}

export function formatDateTime(
  value: string | null | undefined,
  fallback = '-',
): string {
  if (!value) return fallback;
  try {
    return new Date(value).toLocaleString('zh-CN');
  } catch {
    return value;
  }
}

export function formatDateTimeFull(
  value?: string | null,
  fallback = '-',
): string {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}
