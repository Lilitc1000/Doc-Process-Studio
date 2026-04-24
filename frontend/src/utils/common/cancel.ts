export const isRequestCanceled = (error: unknown) => {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return true;
  }
  if (typeof error === 'object' && error !== null) {
    const maybeCode = (error as { code?: unknown }).code;
    if (maybeCode === 'ERR_CANCELED') {
      return true;
    }
    const maybeName = (error as { name?: unknown }).name;
    if (maybeName === 'CanceledError') {
      return true;
    }
  }
  return false;
};
