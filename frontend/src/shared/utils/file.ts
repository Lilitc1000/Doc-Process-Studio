import {
  FILE_TYPE_VISUALS,
  FILE_EXTENSION_VISUAL_MAP,
  MIME_TYPE_CATEGORY_MAP,
} from './file-type-visuals';

export const formatFileSize = (fileOrSize: File | number) => {
  const size = typeof fileOrSize === 'number' ? fileOrSize : fileOrSize.size;

  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const findFileCategoryByExtension = (extension: string) =>
  FILE_EXTENSION_VISUAL_MAP[extension] ?? null;

const findFileCategory = (fileName: string, mimeType?: string) => {
  const normalizedMimeType = mimeType?.trim().toLowerCase() ?? '';
  if (normalizedMimeType) {
    const mimeCategory = MIME_TYPE_CATEGORY_MAP[normalizedMimeType];
    if (mimeCategory) {
      return mimeCategory;
    }

    if (normalizedMimeType.startsWith('image/')) {
      return 'image';
    }

    if (normalizedMimeType.startsWith('audio/')) {
      return 'audio';
    }

    if (normalizedMimeType.startsWith('video/')) {
      return 'video';
    }

    if (normalizedMimeType.startsWith('text/')) {
      return 'text';
    }
  }

  const extension = fileName.includes('.')
    ? (fileName.split('.').pop()?.trim().toLowerCase() ?? '')
    : '';

  if (!extension) {
    return 'file';
  }

  return findFileCategoryByExtension(extension) ?? 'file';
};

export const getFileTypeVisual = (fileName: string, mimeType?: string) => {
  const category = findFileCategory(fileName, mimeType);
  return FILE_TYPE_VISUALS[category] ?? FILE_TYPE_VISUALS.file;
};
