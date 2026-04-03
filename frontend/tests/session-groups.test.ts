import { describe, expect, it } from 'vitest';
import { groupSessionsByDate } from '../src/utils/session-groups';

describe('session groups', () => {
  it('按最近和年月分组历史会话', () => {
    const now = new Date('2026-04-03T12:00:00Z');
    const groups = groupSessionsByDate(
      [
        {
          id: 'recent-1',
          title: '最近的对话',
          created_at: '2026-04-02T10:00:00Z',
          updated_at: '2026-04-02T10:00:00Z',
          selected_processing_mode: 'document-assistant',
          selected_model: 'qwen3:8b',
        },
        {
          id: 'older-1',
          title: '一月的对话',
          created_at: '2026-01-15T10:00:00Z',
          updated_at: '2026-01-20T10:00:00Z',
          selected_processing_mode: 'document-assistant',
          selected_model: 'qwen3:8b',
        },
      ],
      now,
    );

    expect(groups).toHaveLength(2);
    expect(groups[0]).toMatchObject({
      id: 'recent',
      label: '最近',
    });
    expect(groups[0].sessions.map((session) => session.id)).toEqual([
      'recent-1',
    ]);
    expect(groups[1]).toMatchObject({
      id: '2026-1',
      label: '2026年1月',
    });
    expect(groups[1].sessions.map((session) => session.id)).toEqual([
      'older-1',
    ]);
  });
});
