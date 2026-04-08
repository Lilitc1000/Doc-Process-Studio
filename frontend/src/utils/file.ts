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

interface FileTypeVisual {
  badge: string;
  label: string;
  color: string;
  background: string;
  border: string;
}

const FILE_TYPE_VISUALS: Record<string, FileTypeVisual> = {
  pdf: {
    badge: 'PDF',
    label: 'PDF 文档',
    color: '#b42318',
    background: 'linear-gradient(180deg, #fff1f1, #ffe4e6)',
    border: 'rgba(228, 72, 72, 0.24)',
  },
  word: {
    badge: 'DOC',
    label: 'Word 文档',
    color: '#175cd3',
    background: 'linear-gradient(180deg, #eef4ff, #dbeafe)',
    border: 'rgba(37, 99, 235, 0.24)',
  },
  markdown: {
    badge: 'MD',
    label: 'Markdown 文档',
    color: '#155eef',
    background: 'linear-gradient(180deg, #eff8ff, #dbeafe)',
    border: 'rgba(21, 94, 239, 0.22)',
  },
  excel: {
    badge: 'XLS',
    label: '表格文件',
    color: '#027a48',
    background: 'linear-gradient(180deg, #ecfdf3, #dcfce7)',
    border: 'rgba(22, 163, 74, 0.24)',
  },
  ppt: {
    badge: 'PPT',
    label: '演示文稿',
    color: '#c2410c',
    background: 'linear-gradient(180deg, #fff7ed, #ffedd5)',
    border: 'rgba(249, 115, 22, 0.24)',
  },
  image: {
    badge: 'IMG',
    label: '图片文件',
    color: '#7c3aed',
    background: 'linear-gradient(180deg, #f5f3ff, #ede9fe)',
    border: 'rgba(124, 58, 237, 0.22)',
  },
  archive: {
    badge: 'ZIP',
    label: '压缩文件',
    color: '#a16207',
    background: 'linear-gradient(180deg, #fefce8, #fef3c7)',
    border: 'rgba(202, 138, 4, 0.24)',
  },
  vue: {
    badge: 'VUE',
    label: 'Vue 组件',
    color: '#047857',
    background: 'linear-gradient(180deg, #ecfdf3, #d1fae5)',
    border: 'rgba(5, 150, 105, 0.22)',
  },
  typescript: {
    badge: 'TS',
    label: 'TypeScript 文件',
    color: '#175cd3',
    background: 'linear-gradient(180deg, #eef4ff, #dbeafe)',
    border: 'rgba(37, 99, 235, 0.22)',
  },
  javascript: {
    badge: 'JS',
    label: 'JavaScript 文件',
    color: '#a16207',
    background: 'linear-gradient(180deg, #fefce8, #fef3c7)',
    border: 'rgba(202, 138, 4, 0.24)',
  },
  python: {
    badge: 'PY',
    label: 'Python 文件',
    color: '#155eef',
    background: 'linear-gradient(180deg, #eff8ff, #dbeafe)',
    border: 'rgba(21, 94, 239, 0.22)',
  },
  java: {
    badge: 'JAVA',
    label: 'Java 文件',
    color: '#b42318',
    background: 'linear-gradient(180deg, #fff1f1, #ffe4e6)',
    border: 'rgba(228, 72, 72, 0.24)',
  },
  go: {
    badge: 'GO',
    label: 'Go 文件',
    color: '#0f766e',
    background: 'linear-gradient(180deg, #ecfeff, #cffafe)',
    border: 'rgba(13, 148, 136, 0.22)',
  },
  rust: {
    badge: 'RS',
    label: 'Rust 文件',
    color: '#9a3412',
    background: 'linear-gradient(180deg, #fff7ed, #fed7aa)',
    border: 'rgba(234, 88, 12, 0.22)',
  },
  cpp: {
    badge: 'C++',
    label: 'C/C++ 文件',
    color: '#4338ca',
    background: 'linear-gradient(180deg, #eef2ff, #e0e7ff)',
    border: 'rgba(99, 102, 241, 0.22)',
  },
  csharp: {
    badge: 'C#',
    label: 'C# 文件',
    color: '#7c3aed',
    background: 'linear-gradient(180deg, #f5f3ff, #ede9fe)',
    border: 'rgba(124, 58, 237, 0.22)',
  },
  php: {
    badge: 'PHP',
    label: 'PHP 文件',
    color: '#5b21b6',
    background: 'linear-gradient(180deg, #f5f3ff, #ede9fe)',
    border: 'rgba(109, 40, 217, 0.22)',
  },
  ruby: {
    badge: 'RB',
    label: 'Ruby 文件',
    color: '#b42318',
    background: 'linear-gradient(180deg, #fff1f1, #ffe4e6)',
    border: 'rgba(228, 72, 72, 0.24)',
  },
  html: {
    badge: 'HTML',
    label: 'HTML 文件',
    color: '#c2410c',
    background: 'linear-gradient(180deg, #fff7ed, #ffedd5)',
    border: 'rgba(249, 115, 22, 0.24)',
  },
  css: {
    badge: 'CSS',
    label: '样式文件',
    color: '#155eef',
    background: 'linear-gradient(180deg, #eff8ff, #dbeafe)',
    border: 'rgba(21, 94, 239, 0.22)',
  },
  json: {
    badge: 'JSON',
    label: 'JSON 配置',
    color: '#a16207',
    background: 'linear-gradient(180deg, #fefce8, #fef3c7)',
    border: 'rgba(202, 138, 4, 0.24)',
  },
  yaml: {
    badge: 'YAML',
    label: 'YAML 配置',
    color: '#0f766e',
    background: 'linear-gradient(180deg, #ecfeff, #cffafe)',
    border: 'rgba(13, 148, 136, 0.22)',
  },
  xml: {
    badge: 'XML',
    label: 'XML 文件',
    color: '#9a3412',
    background: 'linear-gradient(180deg, #fff7ed, #fed7aa)',
    border: 'rgba(234, 88, 12, 0.22)',
  },
  toml: {
    badge: 'TOML',
    label: 'TOML 配置',
    color: '#7c2d12',
    background: 'linear-gradient(180deg, #fff7ed, #fed7aa)',
    border: 'rgba(194, 65, 12, 0.22)',
  },
  sql: {
    badge: 'SQL',
    label: 'SQL 文件',
    color: '#0f766e',
    background: 'linear-gradient(180deg, #ecfeff, #cffafe)',
    border: 'rgba(13, 148, 136, 0.22)',
  },
  shell: {
    badge: 'SH',
    label: 'Shell 脚本',
    color: '#475467',
    background: 'linear-gradient(180deg, #f8fafc, #eef2f7)',
    border: 'rgba(148, 163, 184, 0.26)',
  },
  code: {
    badge: 'DEV',
    label: '代码文件',
    color: '#155eef',
    background: 'linear-gradient(180deg, #eff8ff, #dbeafe)',
    border: 'rgba(21, 94, 239, 0.22)',
  },
  text: {
    badge: 'TXT',
    label: '文本文件',
    color: '#475467',
    background: 'linear-gradient(180deg, #f8fafc, #eef2f7)',
    border: 'rgba(148, 163, 184, 0.26)',
  },
  audio: {
    badge: 'AUD',
    label: '音频文件',
    color: '#0f766e',
    background: 'linear-gradient(180deg, #ecfeff, #cffafe)',
    border: 'rgba(13, 148, 136, 0.22)',
  },
  video: {
    badge: 'VID',
    label: '视频文件',
    color: '#be185d',
    background: 'linear-gradient(180deg, #fff1f2, #ffe4e6)',
    border: 'rgba(225, 29, 72, 0.22)',
  },
  file: {
    badge: 'FILE',
    label: '文件',
    color: '#475467',
    background: 'linear-gradient(180deg, #f8fafc, #eef2f7)',
    border: 'rgba(148, 163, 184, 0.26)',
  },
};

const FILE_EXTENSION_VISUAL_MAP: Record<string, string> = {
  pdf: 'pdf',
  doc: 'word',
  docx: 'word',
  wps: 'word',
  odt: 'word',
  rtf: 'word',
  md: 'markdown',
  markdown: 'markdown',
  txt: 'text',
  log: 'text',
  csv: 'excel',
  xls: 'excel',
  xlsx: 'excel',
  ods: 'excel',
  ppt: 'ppt',
  pptx: 'ppt',
  odp: 'ppt',
  key: 'ppt',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  gif: 'image',
  bmp: 'image',
  webp: 'image',
  svg: 'image',
  ico: 'image',
  heic: 'image',
  zip: 'archive',
  rar: 'archive',
  '7z': 'archive',
  tar: 'archive',
  gz: 'archive',
  tgz: 'archive',
  bz2: 'archive',
  xz: 'archive',
  vue: 'vue',
  ts: 'typescript',
  tsx: 'typescript',
  mts: 'typescript',
  cts: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  py: 'python',
  java: 'java',
  go: 'go',
  rs: 'rust',
  c: 'cpp',
  cc: 'cpp',
  cpp: 'cpp',
  h: 'cpp',
  hpp: 'cpp',
  cs: 'csharp',
  php: 'php',
  rb: 'ruby',
  html: 'html',
  htm: 'html',
  css: 'css',
  scss: 'css',
  less: 'css',
  json: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  xml: 'xml',
  toml: 'toml',
  ini: 'toml',
  conf: 'toml',
  sql: 'sql',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  ps1: 'shell',
  bat: 'shell',
  cmd: 'shell',
  mp3: 'audio',
  wav: 'audio',
  m4a: 'audio',
  aac: 'audio',
  flac: 'audio',
  ogg: 'audio',
  mp4: 'video',
  mov: 'video',
  avi: 'video',
  mkv: 'video',
  webm: 'video',
  wmv: 'video',
};

const MIME_TYPE_CATEGORY_MAP: Record<string, string> = {
  'application/pdf': 'pdf',
  'application/msword': 'word',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
    'word',
  'application/vnd.ms-excel': 'excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel',
  'text/csv': 'excel',
  'application/vnd.ms-powerpoint': 'ppt',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation':
    'ppt',
  'application/zip': 'archive',
  'application/x-zip-compressed': 'archive',
  'application/json': 'json',
  'text/markdown': 'markdown',
  'text/plain': 'text',
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
