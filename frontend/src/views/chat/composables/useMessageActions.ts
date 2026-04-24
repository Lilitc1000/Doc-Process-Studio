import { useChatStore } from '../../../stores/chat';
import { useAppStore } from '../../../stores/app';
import { downloadAttachment } from '../../../api/chat-attachments';
import type {
  ChatAttachment,
  ChatEditAttachment,
  ChatRequestSnapshot,
} from '../../../types/chat/chat';
import { formatFileSize } from '../../../utils/common/file';
import { triggerBlobDownload } from '../../../utils/common/download';
import { getErrorMessage } from '../../../utils/common/error';

interface UseMessageActionsOptions {
  executeAssistantGeneration: (
    requestSnapshot: ChatRequestSnapshot,
  ) => Promise<void>;
  scrollToBottom: () => void;
  persistCurrentSession: () => Promise<unknown>;
  onStopGeneration: () => void;
  showCopyToast: (message: string, options?: { title?: string }) => void;
}

export const useMessageActions = (options: UseMessageActionsOptions) => {
  const chatStore = useChatStore();
  const appStore = useAppStore();

  const createAttachmentPreview = (files: File[]): ChatAttachment[] => {
    return files.map((file) => ({
      name: file.name,
      sizeLabel: formatFileSize(file),
      mimeType: file.type,
      source: 'uploaded',
    }));
  };

  const createEditableAttachmentPreview = (
    files: File[],
  ): ChatEditAttachment[] => {
    return files.map((file) => ({
      name: file.name,
      sizeLabel: formatFileSize(file),
      mimeType: file.type,
      source: 'uploaded',
      requestFile: file,
    }));
  };

  const createUserApiContent = (
    text: string,
    files: Array<{ name: string }>,
  ) => {
    const trimmedText = text.trim();
    if (files.length === 0) {
      return trimmedText;
    }

    const fileNames = files.map((file) => file.name).join('、');
    const fileSummary = `[用户上传了 ${files.length} 个文件：${fileNames}]`;

    if (!trimmedText) {
      return `请结合我上传的文件进行处理。\n${fileSummary}`;
    }

    return `${trimmedText}\n${fileSummary}`;
  };

  const onFilesSelect = (files: File[]) => {
    chatStore.selectedFiles = [...chatStore.selectedFiles, ...files];
  };

  const onRemoveFile = (index: number) => {
    chatStore.selectedFiles.splice(index, 1);
  };

  const onClearAllFiles = () => {
    chatStore.selectedFiles = [];
  };

  const onClearChat = () => {
    options.onStopGeneration();
    chatStore.resetChatState();
  };

  const startEditingMessage = (messageId: string) => {
    if (chatStore.isLoading) {
      return;
    }

    const messageNode = chatStore.findMessageById(messageId);
    if (!messageNode || messageNode.role !== 'user') {
      return;
    }

    chatStore.editingMessageId = messageId;
    chatStore.editingDraftText = messageNode.content;
    chatStore.editingDraftSkillIds = [...(messageNode.requestSkillIds ?? [])];
    const requestFileEntries: Array<[string, File]> = (
      messageNode.requestFiles ?? []
    ).map((file: File) => [`${file.name}::${formatFileSize(file)}`, file]);
    const requestFileMap = new Map<string, File>(requestFileEntries);
    const sourceFiles =
      messageNode.files && messageNode.files.length > 0
        ? messageNode.files
        : createAttachmentPreview(messageNode.requestFiles ?? []);

    chatStore.editingDraftFiles = sourceFiles.map<ChatEditAttachment>(
      (file) => ({
        ...file,
        requestFile:
          requestFileMap.get(`${file.name}::${file.sizeLabel}`) ?? null,
      }),
    );
  };

  const updateEditingText = (value: string) => {
    chatStore.editingDraftText = value;
  };

  const appendEditingFiles = (files: File[]) => {
    chatStore.editingDraftFiles = [
      ...chatStore.editingDraftFiles,
      ...createEditableAttachmentPreview(files),
    ];
  };

  const removeEditingFile = (index: number) => {
    chatStore.editingDraftFiles.splice(index, 1);
  };

  const cancelEditingMessage = () => {
    chatStore.resetEditingState();
  };

  const confirmEditingMessage = async () => {
    if (!chatStore.editingMessageId || !chatStore.canConfirmEdit) {
      return;
    }

    const sourceMessage = chatStore.findMessageById(chatStore.editingMessageId);
    if (!sourceMessage || sourceMessage.role !== 'user') {
      chatStore.resetEditingState();
      return;
    }

    const nextText = chatStore.editingDraftText.trim();
    const nextFiles = chatStore.editingDraftFiles.flatMap((file) => {
      return file.requestFile ? [file.requestFile] : [];
    });
    const nextSkillIds = [...chatStore.editingDraftSkillIds];
    const nextAttachments = chatStore.editingDraftFiles.map((file) => ({
      name: file.name,
      sizeLabel: file.sizeLabel,
      attachmentId: file.attachmentId,
      downloadUrl: file.downloadUrl,
      expiresAt: file.expiresAt,
      mimeType: file.mimeType,
      source: file.source,
    }));

    const editedUserMessage = chatStore.createMessageNode({
      role: 'user',
      content: nextText,
      apiContent: createUserApiContent(nextText, nextAttachments),
      files: nextAttachments,
      requestFiles: nextFiles,
      requestSkillIds: nextSkillIds,
      timestamp: new Date(),
      parentId: sourceMessage.parentId,
    });

    chatStore.resetEditingState();
    options.scrollToBottom();
    await options.persistCurrentSession();

    await options.executeAssistantGeneration(
      chatStore.buildRequestSnapshotForUserMessage(
        editedUserMessage.id,
        appStore.selectedModel,
        appStore.selectedRerankerModel,
      ),
    );
  };

  const onSendMessage = async () => {
    const text = chatStore.inputText.trim();
    if (
      (!text && chatStore.selectedFiles.length === 0) ||
      chatStore.isLoading
    ) {
      return;
    }

    const currentRequestFiles = [...chatStore.selectedFiles];
    const currentRequestSkillIds = [...chatStore.selectedSkillIds];
    const userMessage = chatStore.createMessageNode({
      role: 'user',
      content: text,
      apiContent: createUserApiContent(text, currentRequestFiles),
      files: createAttachmentPreview(currentRequestFiles),
      requestFiles: currentRequestFiles,
      requestSkillIds: currentRequestSkillIds,
      timestamp: new Date(),
      parentId: chatStore.currentLeafMessageId,
    });
    options.scrollToBottom();

    chatStore.inputText = '';
    chatStore.selectedFiles = [];
    chatStore.selectedSkillIds = [];
    chatStore.activeSessionId = chatStore.conversationId;
    await options.persistCurrentSession();

    await options.executeAssistantGeneration(
      chatStore.buildRequestSnapshotForUserMessage(
        userMessage.id,
        appStore.selectedModel,
        appStore.selectedRerankerModel,
      ),
    );
  };

  const onRegenerate = async (assistantMessageId: string) => {
    if (chatStore.isLoading) {
      return;
    }

    const assistantNode = chatStore.findMessageById(assistantMessageId);
    if (!assistantNode?.parentId || assistantNode.role !== 'assistant') {
      return;
    }

    await options.persistCurrentSession();
    await options.executeAssistantGeneration(
      chatStore.buildRequestSnapshotForUserMessage(
        assistantNode.parentId,
        appStore.selectedModel,
        appStore.selectedRerankerModel,
      ),
    );
  };

  const copyMessage = async (messageId: string) => {
    const messageNode = chatStore.findMessageById(messageId);
    if (!messageNode?.content.trim() || !navigator.clipboard) {
      return;
    }

    try {
      await navigator.clipboard.writeText(messageNode.content);
      options.showCopyToast('内容已复制到剪贴板');
    } catch (error) {
      console.error('复制消息失败。', error);
    }
  };

  const downloadAssistantMessage = (assistantMessageId: string) => {
    const assistantNode = chatStore.findMessageById(assistantMessageId);
    if (!assistantNode?.content.trim()) {
      return;
    }

    const blob = new Blob([assistantNode.content], {
      type: 'text/markdown;charset=utf-8',
    });
    const safeTimestamp = assistantNode.timestamp
      .toISOString()
      .replace(/[:.]/g, '-');
    triggerBlobDownload(blob, `assistant-reply-${safeTimestamp}.md`);
  };

  const downloadMessageFile = async (file: ChatAttachment) => {
    if (!file.attachmentId) {
      return;
    }

    try {
      await downloadAttachment(file.attachmentId);
    } catch (error) {
      const errorMessage = getErrorMessage(error, '下载文件失败，请稍后重试。');
      options.showCopyToast(errorMessage, { title: '下载失败' });
    }
  };

  return {
    onFilesSelect,
    onRemoveFile,
    onClearAllFiles,
    onClearChat,
    startEditingMessage,
    updateEditingText,
    appendEditingFiles,
    removeEditingFile,
    cancelEditingMessage,
    confirmEditingMessage,
    onSendMessage,
    onRegenerate,
    copyMessage,
    downloadAssistantMessage,
    downloadMessageFile,
  };
};
