import { describe, expect, it } from 'vitest';
import { AVATAR_COLORS } from '@shared/utils/avatar-colors';

describe('AVATAR_COLORS', () => {
  it('包含至少 6 种颜色', () => {
    expect(AVATAR_COLORS.length).toBeGreaterThanOrEqual(6);
  });

  it('每个颜色是有效的十六进制格式', () => {
    for (const color of AVATAR_COLORS) {
      expect(color).toMatch(/^#[0-9a-f]{6}$/);
    }
  });

  it('颜色不重复', () => {
    const unique = new Set(AVATAR_COLORS);
    expect(unique.size).toBe(AVATAR_COLORS.length);
  });

  it('包含默认颜色 #4f46e5', () => {
    expect(AVATAR_COLORS).toContain('#4f46e5');
  });
});
