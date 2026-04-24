import { apiClient } from './request';
import { triggerBlobDownload } from '../utils/common/download';

const parseDownloadFilename = (contentDisposition: string | null) => {
  if (!contentDisposition) {
    return null;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  if (plainMatch?.[1]) {
    return plainMatch[1];
  }

  return null;
};

export const downloadAttachment = async (attachmentId: string) => {
  const response = await apiClient.get(
    `/attachments/${attachmentId}/download`,
    {
      responseType: 'blob',
      validateStatus: () => true,
    },
  );

  if (response.status === 410) {
    throw new Error('该文件已过期，请重新生成。');
  }

  if (response.status !== 200) {
    throw new Error('下载文件失败，请稍后重试。');
  }

  const downloadName =
    parseDownloadFilename(response.headers['content-disposition'] ?? null) ??
    'download.bin';

  triggerBlobDownload(response.data, downloadName);
};
