import type { ChatMessageNode, ChatMessageRole } from '../types/chat';

interface DisplayedMessagesOptions {
  messageNodes: Record<string, ChatMessageNode>;
  rootChildIds: string[];
  selectedRootChildId: string | null;
  selectedChildIdByParent: Record<string, string>;
  fallbackMessages: ChatMessageNode[];
}

interface MessageSiblingOptions {
  messageNodes: Record<string, ChatMessageNode>;
  rootChildIds: string[];
  messageId: string;
}

export const getNodeById = (
  messageNodes: Record<string, ChatMessageNode>,
  messageId: string,
) => {
  return messageNodes[messageId] ?? null;
};

export const getSelectedChildId = (
  messageNodes: Record<string, ChatMessageNode>,
  selectedChildIdByParent: Record<string, string>,
  messageId: string,
) => {
  const currentNode = getNodeById(messageNodes, messageId);
  if (!currentNode || currentNode.childIds.length === 0) {
    return null;
  }
  return selectedChildIdByParent[messageId] ?? currentNode.childIds[0] ?? null;
};

export const buildDisplayedMessages = (options: DisplayedMessagesOptions) => {
  const rootMessageId =
    options.selectedRootChildId ?? options.rootChildIds[0] ?? null;
  if (!rootMessageId) {
    return options.fallbackMessages;
  }

  const visibleMessages: ChatMessageNode[] = [];
  let currentMessageId: string | null = rootMessageId;

  while (currentMessageId) {
    const currentNode = getNodeById(options.messageNodes, currentMessageId);
    if (!currentNode) {
      break;
    }
    visibleMessages.push(currentNode);
    currentMessageId = getSelectedChildId(
      options.messageNodes,
      options.selectedChildIdByParent,
      currentNode.id,
    );
  }

  return visibleMessages;
};

export const getMessagePathToNode = (
  messageNodes: Record<string, ChatMessageNode>,
  messageId: string,
) => {
  const path: ChatMessageNode[] = [];
  let currentMessageId: string | null = messageId;

  while (currentMessageId !== null) {
    const currentNode = getNodeById(messageNodes, currentMessageId);
    if (!currentNode) {
      break;
    }
    path.push(currentNode);
    currentMessageId = currentNode.parentId;
  }

  return path.reverse();
};

export const collectPersistedUploadedAttachmentIdsFromPath = (
  path: ChatMessageNode[],
) => {
  const attachmentIds: string[] = [];

  for (const message of path) {
    for (const file of message.files ?? []) {
      const normalizedAttachmentId = file.attachmentId?.trim();
      const isUploadedAttachment =
        file.source === 'uploaded' || (!file.source && message.role === 'user');
      if (
        normalizedAttachmentId &&
        isUploadedAttachment &&
        !attachmentIds.includes(normalizedAttachmentId)
      ) {
        attachmentIds.push(normalizedAttachmentId);
      }
    }
  }

  return attachmentIds;
};

export const getMessageSiblingIds = (options: MessageSiblingOptions) => {
  const messageNode = getNodeById(options.messageNodes, options.messageId);
  if (!messageNode) {
    return [];
  }

  const siblingSourceIds = messageNode.parentId
    ? (getNodeById(options.messageNodes, messageNode.parentId)?.childIds ?? [])
    : options.rootChildIds;

  return siblingSourceIds.filter((childId) => {
    return (
      getNodeById(options.messageNodes, childId)?.role === messageNode.role
    );
  });
};

export const getMessageVersionCount = (options: MessageSiblingOptions) => {
  return getMessageSiblingIds(options).length;
};

export const getMessageVersionIndex = (options: MessageSiblingOptions) => {
  const siblingIds = getMessageSiblingIds(options);
  const currentIndex = siblingIds.indexOf(options.messageId);
  return currentIndex >= 0 ? currentIndex + 1 : 1;
};

export const canSwitchMessageVersion = (
  options: MessageSiblingOptions & { direction: -1 | 1 },
) => {
  const siblingIds = getMessageSiblingIds(options);
  const currentIndex = siblingIds.indexOf(options.messageId);
  const targetIndex = currentIndex + options.direction;
  return targetIndex >= 0 && targetIndex < siblingIds.length;
};

export const resolveTargetVersionMessageId = (
  options: MessageSiblingOptions & { direction: -1 | 1 },
) => {
  const siblingIds = getMessageSiblingIds(options);
  const currentIndex = siblingIds.indexOf(options.messageId);
  return siblingIds[currentIndex + options.direction] ?? null;
};

export const findAdjacentVersionNodes = (options: {
  displayedMessages: ChatMessageNode[];
  messageNodes: Record<string, ChatMessageNode>;
  rootChildIds: string[];
}) => {
  const versionCandidates: ChatMessageNode[] = [];

  for (const message of options.displayedMessages) {
    const siblingIds = getMessageSiblingIds({
      messageNodes: options.messageNodes,
      rootChildIds: options.rootChildIds,
      messageId: message.id,
    });
    const currentIndex = siblingIds.indexOf(message.id);
    if (currentIndex < 0) {
      continue;
    }

    const adjacentSiblingIds = [
      siblingIds[currentIndex - 1] ?? null,
      siblingIds[currentIndex + 1] ?? null,
    ];

    for (const siblingId of adjacentSiblingIds) {
      if (!siblingId) {
        continue;
      }
      const siblingNode = getNodeById(options.messageNodes, siblingId);
      if (siblingNode) {
        versionCandidates.push(siblingNode);
      }
    }
  }

  return versionCandidates;
};

export const resolveCurrentLeafMessageId = (
  rootChildIds: string[],
  displayedMessages: ChatMessageNode[],
) => {
  if (rootChildIds.length === 0) {
    return null;
  }
  const lastMessage = displayedMessages[displayedMessages.length - 1] ?? null;
  return lastMessage?.id ?? null;
};

export const resolveLastRoleMessageId = (
  displayedMessages: ChatMessageNode[],
  role: ChatMessageRole,
) => {
  for (let index = displayedMessages.length - 1; index >= 0; index -= 1) {
    const message = displayedMessages[index];
    if (message?.role === role) {
      return message.id;
    }
  }
  return null;
};
