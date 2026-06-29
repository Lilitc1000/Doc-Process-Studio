interface SessionGroupItem {
  id: string;
  title: string;
  createdAt?: string;
  updatedAt?: string;
  status?: string;
  statusLabel?: string;
  [key: string]: unknown;
}

interface SessionGroup {
  id: string;
  label: string;
  sessions: SessionGroupItem[];
}

export const groupSessionsByDate = (
  sessions: readonly SessionGroupItem[],
  options?: {
    dateField?: 'updatedAt' | 'createdAt';
  },
  now = new Date(),
) => {
  const dateField = options?.dateField ?? 'updatedAt';
  const nowTime = now.getTime();
  const recentThreshold = nowTime - 30 * 24 * 60 * 60 * 1000;
  const groups: SessionGroup[] = [];
  const recentSessions: SessionGroupItem[] = [];
  const olderGroups = new Map<string, SessionGroup>();

  for (const session of sessions) {
    const rawDate = session[dateField as keyof SessionGroupItem] as
      | string
      | undefined;
    const dateValue = rawDate ? new Date(rawDate).getTime() : NaN;
    if (!Number.isFinite(dateValue) || dateValue >= recentThreshold) {
      recentSessions.push(session);
      continue;
    }

    const date = new Date(dateValue);
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
