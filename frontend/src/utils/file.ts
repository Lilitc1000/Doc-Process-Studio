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
