type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: string;
  requestId?: string;
  error?: unknown;
  [key: string]: unknown;
}

function formatTime(date: Date): string {
  return date.toISOString().replace('T', ' ').replace('Z', '');
}

function formatEntry(entry: LogEntry): string {
  const { timestamp, level, message, context, requestId, error, ...rest } =
    entry;
  const tag = context ? ` [${context}]` : '';
  const rid = requestId ? ` req=${requestId}` : '';
  const extra = Object.keys(rest).length > 0 ? ` ${JSON.stringify(rest)}` : '';

  let line = `${timestamp} | ${level.toUpperCase().padEnd(5)} |${tag}${rid} ${message}${extra}`;

  if (error instanceof Error) {
    line += `\n  ${error.stack ?? error.message}`;
  } else if (error != null) {
    line += `\n  ${String(error)}`;
  }

  return line;
}

function buildEntry(
  level: LogLevel,
  message: string,
  details?: Record<string, unknown>,
): LogEntry {
  const entry: LogEntry = {
    timestamp: formatTime(new Date()),
    level,
    message,
  };

  if (details) {
    for (const [key, value] of Object.entries(details)) {
      if (value !== undefined) {
        entry[key] = value;
      }
    }
  }

  return entry;
}

function output(entry: LogEntry): void {
  const text = formatEntry(entry);
  switch (entry.level) {
    case 'debug':
      console.debug(text);
      break;
    case 'info':
      console.info(text);
      break;
    case 'warn':
      console.warn(text);
      break;
    case 'error':
      console.error(text);
      break;
  }
}

export const logger = {
  debug(message: string, details?: Record<string, unknown>): void {
    output(buildEntry('debug', message, details));
  },

  info(message: string, details?: Record<string, unknown>): void {
    output(buildEntry('info', message, details));
  },

  warn(message: string, details?: Record<string, unknown>): void {
    output(buildEntry('warn', message, details));
  },

  error(message: string, details?: Record<string, unknown>): void {
    output(buildEntry('error', message, details));
  },
};
