import { useChatStore } from '../../../stores/chat';
import { useAppStore } from '../../../stores/app';
import {
  fetchSessionDetail,
  fetchSessionSummaries,
  removeSession,
  renameSession,
  saveSession,
} from '../../../api/chat-sessions';
import { logger } from '../../../utils/common/logger';

interface UseChatSessionsOptions {
  afterSessionLoaded?: () => Promise<void> | void;
  onDeleteActiveSession?: () => void;
}

export const useChatSessions = (options?: UseChatSessionsOptions) => {
  const chatStore = useChatStore();
  const appStore = useAppStore();

  const loadSessionSummaries = async () => {
    try {
      const sessions = await fetchSessionSummaries();
      chatStore.sessionSummaries = [...sessions].sort((left, right) => {
        return (
          new Date(right.updatedAt).getTime() -
          new Date(left.updatedAt).getTime()
        );
      });
    } catch (error) {
      logger.error('加载历史会话列表失败。', {
        context: 'useChatSessions',
        error,
      });
    }
  };

  const persistCurrentSession = async (optionsWithTitle?: {
    title?: string;
  }) => {
    if (chatStore.rootChildIds.length === 0) {
      return null;
    }

    const sessionId = chatStore.activeSessionId ?? chatStore.conversationId;
    chatStore.activeSessionId = sessionId;

    try {
      const sessionSummary = await saveSession(sessionId, {
        title: optionsWithTitle?.title ?? '',
        titleSourceMessages: chatStore.buildTitleSourceMessages(),
        snapshot: chatStore.buildSessionSnapshotPayload(
          appStore.selectedModel,
          appStore.selectedRerankerModel,
        ),
      });
      chatStore.mergeSessionSummary(sessionSummary);
      return sessionSummary;
    } catch (error) {
      logger.error('保存历史会话失败。', {
        context: 'useChatSessions',
        error,
        sessionId,
      });
      return null;
    }
  };

  const loadChatSession = async (sessionId: string) => {
    if (chatStore.isLoading) {
      return;
    }

    try {
      const sessionDetail = await fetchSessionDetail(sessionId);
      chatStore.hydrateSessionSnapshot(sessionDetail.snapshot);
      chatStore.activeSessionId = sessionDetail.id;
      chatStore.conversationId = sessionDetail.id;
      appStore.selectedModel = sessionDetail.snapshot.selectedModel;
      appStore.selectedRerankerModel =
        sessionDetail.snapshot.selectedRerankerModel ??
        sessionDetail.snapshot.selectedModel;
      chatStore.mergeSessionSummary(sessionDetail);
      chatStore.bumpSessionViewKey();
      await options?.afterSessionLoaded?.();
    } catch (error) {
      logger.error('加载历史会话失败。', {
        context: 'useChatSessions',
        error,
        sessionId,
      });
    }
  };

  const renameChatSession = async (sessionId: string, title: string) => {
    try {
      const sessionSummary = await renameSession(sessionId, title);
      chatStore.mergeSessionSummary(sessionSummary);
    } catch (error) {
      logger.error('修改历史会话标题失败。', {
        context: 'useChatSessions',
        error,
        sessionId,
      });
    }
  };

  const deleteChatSession = async (sessionId: string) => {
    try {
      await removeSession(sessionId);
      chatStore.sessionSummaries = chatStore.sessionSummaries.filter(
        (session) => {
          return session.id !== sessionId;
        },
      );

      if (chatStore.activeSessionId === sessionId) {
        options?.onDeleteActiveSession?.();
      }
    } catch (error) {
      logger.error('删除历史会话失败。', {
        context: 'useChatSessions',
        error,
        sessionId,
      });
    }
  };

  return {
    deleteChatSession,
    loadChatSession,
    loadSessionSummaries,
    persistCurrentSession,
    renameChatSession,
  };
};
