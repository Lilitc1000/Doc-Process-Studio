import type { ChatSessionSummary, SessionGroup } from '../types/session';

export const groupSessionsByDate = (
  sessions: readonly ChatSessionSummary[],
  now = new Date(),
) => {
  const nowTime = now.getTime();
  const recentThreshold = nowTime - 30 * 24 * 60 * 60 * 1000;
  const groups: SessionGroup[] = [];
  const recentSessions: ChatSessionSummary[] = [];
  const olderGroups = new Map<string, SessionGroup>();

  for (const session of sessions) {
    const updatedAt = new Date(session.updated_at).getTime();
    if (!Number.isFinite(updatedAt) || updatedAt >= recentThreshold) {
      recentSessions.push(session);
      continue;
    }

    const date = new Date(updatedAt);
    const groupId = `${date.getFullYear()}-${date.getMonth() + 1}`;
    const existingGroup = olderGroups.get(groupId);
    if (existingGroup) {
      existingGroup.sessions.push(session);
      continue;
    }

    olderGroups.set(groupId, {
      id: groupId,
      label: `${date.getFullYear()}年${date.getMonth() + 1}月`,
      sessions: [session],
    });
  }

  if (recentSessions.length > 0) {
    groups.push({
      id: 'recent',
      label: '最近',
      sessions: recentSessions,
    });
  }

  return groups.concat(Array.from(olderGroups.values()));
};
