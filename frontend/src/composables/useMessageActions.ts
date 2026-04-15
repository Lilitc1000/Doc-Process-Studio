import { computed, type Ref } from 'vue';
import type {
  ChatAttachment,
  ChatEditAttachment,
  ChatMessageNode,
  ChatRequestSnapshot,
} from '../types/chat';
import { formatFileSize } from '../utils/file';

interface UseMessageActionsOptions {
  inputText: Ref<string>;
  selectedFiles: Ref<File[]>;
  selectedSkillIds: Ref<string[]>;
  editingMessageId: Ref<string | null>;
  editingDraftText: Ref<string>;
  editingDraftFiles: Ref<ChatEditAttachment[]>;
  editingDraftSkillIds: Ref<string[]>;
  isLoading: Ref<boolean>;
  activeSessionId: Ref<string | null>;
  conversationId: Ref<string>;
  rootChildIds: Ref<string[]>;
  messageNodes: Ref<Record<string, ChatMessageNode>>;
  selectedRootChildId: Ref<string | null>;
  selectedChildIdByParent: Ref<Record<string, string>>;
  currentLeafMessageId: Ref<string | null>;
  getNodeById: (messageId: string) => ChatMessageNode | null;
  createMessageNode: (
    node: Omit<ChatMessageNode, 'id' | 'childIds'> & { id?: string },
  ) => ChatMessageNode;
  buildRequestSnapshotForUserMessage: (
    userMessageId: string,
  ) => ChatRequestSnapshot;
  executeAssistantGeneration: (
    requestSnapshot: ChatRequestSnapshot,
  ) => Promise<void>;
  persistCurrentSession: () => Promise<unknown>;
  resetEditingState: () => void;
  scrollToBottom: () => void;
  onStopGeneration: () => void;
  resetConversationState: () => void;
  showCopyToast: (message: string, options?: { title?: string }) => void;
  downloadAttachment: (attachmentId: string) => Promise<void>;
}

export const useMessageActions = (options: UseMessageActionsOptions) => {
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

  const canConfirmEdit = computed(() => {
    return (
      !options.isLoading.value &&
      (options.editingDraftText.value.trim().length > 0 ||
        options.editingDraftFiles.value.length > 0)
    );
  });

  const onFilesSelect = (files: File[]) => {
    options.selectedFiles.value = [...options.selectedFiles.value, ...files];
  };

  const onRemoveFile = (index: number) => {
    options.selectedFiles.value.splice(index, 1);
  };

  const onClearAllFiles = () => {
    options.selectedFiles.value = [];
  };

  const onClearChat = () => {
    options.onStopGeneration();
    options.messageNodes.value = {};
    options.rootChildIds.value = [];
    options.selectedRootChildId.value = null;
    options.selectedChildIdByParent.value = {};
    options.selectedFiles.value = [];
    options.selectedSkillIds.value = [];
    options.resetConversationState();
    options.resetEditingState();
  };

  const startEditingMessage = (messageId: string) => {
    if (options.isLoading.value) {
      return;
    }

    const messageNode = options.getNodeById(messageId);
    if (!messageNode || messageNode.role !== 'user') {
      return;
    }

    options.editingMessageId.value = messageId;
    options.editingDraftText.value = messageNode.content;
    options.editingDraftSkillIds.value = [
      ...(messageNode.requestSkillIds ?? []),
    ];
    const requestFileEntries: Array<[string, File]> = (
      messageNode.requestFiles ?? []
    ).map((file) => [`${file.name}::${formatFileSize(file)}`, file]);
    const requestFileMap = new Map<string, File>(requestFileEntries);
    const sourceFiles =
      messageNode.files && messageNode.files.length > 0
        ? messageNode.files
        : createAttachmentPreview(messageNode.requestFiles ?? []);

    options.editingDraftFiles.value = sourceFiles.map<ChatEditAttachment>(
      (file) => ({
        ...file,
        requestFile:
          requestFileMap.get(`${file.name}::${file.sizeLabel}`) ?? null,
      }),
    );
  };

  const updateEditingText = (value: string) => {
    options.editingDraftText.value = value;
  };

  const appendEditingFiles = (files: File[]) => {
    options.editingDraftFiles.value = [
      ...options.editingDraftFiles.value,
      ...createEditableAttachmentPreview(files),
    ];
  };

  const removeEditingFile = (index: number) => {
    options.editingDraftFiles.value.splice(index, 1);
  };

  const cancelEditingMessage = () => {
    options.resetEditingState();
  };

  const confirmEditingMessage = async () => {
    if (!options.editingMessageId.value || !canConfirmEdit.value) {
      return;
    }

    const sourceMessage = options.getNodeById(options.editingMessageId.value);
    if (!sourceMessage || sourceMessage.role !== 'user') {
      options.resetEditingState();
      return;
    }

    const nextText = options.editingDraftText.value.trim();
    const nextFiles = options.editingDraftFiles.value.flatMap((file) => {
      return file.requestFile ? [file.requestFile] : [];
    });
    const nextSkillIds = [...options.editingDraftSkillIds.value];
    const nextAttachments = options.editingDraftFiles.value.map((file) => ({
      name: file.name,
      sizeLabel: file.sizeLabel,
      attachmentId: file.attachmentId,
      downloadUrl: file.downloadUrl,
      expiresAt: file.expiresAt,
      mimeType: file.mimeType,
      source: file.source,
    }));

    const editedUserMessage = options.createMessageNode({
      role: 'user',
      content: nextText,
      apiContent: createUserApiContent(nextText, nextAttachments),
      files: nextAttachments,
      requestFiles: nextFiles,
      requestSkillIds: nextSkillIds,
      timestamp: new Date(),
      parentId: sourceMessage.parentId,
    });

    options.resetEditingState();
    options.scrollToBottom();
    await options.persistCurrentSession();

    await options.executeAssistantGeneration(
      options.buildRequestSnapshotForUserMessage(editedUserMessage.id),
    );
  };

  const onSendMessage = async () => {
    const text = options.inputText.value.trim();
    if (
      (!text && options.selectedFiles.value.length === 0) ||
      options.isLoading.value
    ) {
      return;
    }

    const currentRequestFiles = [...options.selectedFiles.value];
    const currentRequestSkillIds = [...options.selectedSkillIds.value];
    const userMessage = options.createMessageNode({
      role: 'user',
      content: text,
      apiContent: createUserApiContent(text, currentRequestFiles),
      files: createAttachmentPreview(currentRequestFiles),
      requestFiles: currentRequestFiles,
      requestSkillIds: currentRequestSkillIds,
      timestamp: new Date(),
      parentId: options.currentLeafMessageId.value,
    });
    options.scrollToBottom();

    options.inputText.value = '';
    options.selectedFiles.value = [];
    options.selectedSkillIds.value = [];
    options.activeSessionId.value = options.conversationId.value;
    await options.persistCurrentSession();

    await options.executeAssistantGeneration(
      options.buildRequestSnapshotForUserMessage(userMessage.id),
    );
  };

  const onRegenerate = async (assistantMessageId: string) => {
    if (options.isLoading.value) {
      return;
    }

    const assistantNode = options.getNodeById(assistantMessageId);
    if (!assistantNode?.parentId || assistantNode.role !== 'assistant') {
      return;
    }

    await options.persistCurrentSession();
    await options.executeAssistantGeneration(
      options.buildRequestSnapshotForUserMessage(assistantNode.parentId),
    );
  };

  const copyMessage = async (messageId: string) => {
    const messageNode = options.getNodeById(messageId);
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
    const assistantNode = options.getNodeById(assistantMessageId);
    if (!assistantNode?.content.trim()) {
      return;
    }

    const blob = new Blob([assistantNode.content], {
      type: 'text/markdown;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const safeTimestamp = assistantNode.timestamp
      .toISOString()
      .replace(/[:.]/g, '-');

    link.href = url;
    link.download = `assistant-reply-${safeTimestamp}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const downloadMessageFile = async (file: ChatAttachment) => {
    if (!file.attachmentId) {
      return;
    }

    try {
      await options.downloadAttachment(file.attachmentId);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : '下载文件失败，请稍后重试。';
      options.showCopyToast(errorMessage, { title: '下载失败' });
    }
  };

  return {
    canConfirmEdit,
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
