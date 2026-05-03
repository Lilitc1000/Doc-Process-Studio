interface AxiosErrorLike {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

function isAxiosErrorLike(error: unknown): error is AxiosErrorLike {
  return typeof error === 'object' && error !== null && 'response' in error;
}

export const getErrorMessage = (error: unknown, fallback: string) => {
  if (isAxiosErrorLike(error)) {
    return error.response?.data?.detail || error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
};
