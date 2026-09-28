/**
 * 设置模块类型定义。
 *
 * 契约提醒：后端 API 一律 **snake_case**，由 `@shared/api/request` 的 axios 拦截器
 * （humps）自动转换，所以这里写 camelCase 即可。
 *
 * 安全约定：**任何类型里都不存在"明文密钥"字段**。后端只在保存时接收明文，
 * 读取时永远只返回 `maskedValue`（掩码）+ `configured`（是否已配置）+
 * `hint`（尾 4 位，明文过短时为 null）。眼睛图标只作用于用户**正在输入**的内容。
 */

/** 凭据当前来源：system=管理员在设置页写入的共享密钥，none=未配置（已去除环境变量兜底） */
export type SecretSource = 'system' | 'none';

/** 配置项来源：system=库里配置，default=内置默认值（已去除环境变量兜底） */
export type SettingValueSource = 'system' | 'default';

export interface ModelPreferences {
  /** 生成模型名；null 表示用户没设过，前端回落到默认 */
  selected: string | null;
  /** 重排序模型名；null 同上 */
  reranker: string | null;
}

/** 用户级非敏感偏好 */
export interface UserPreferences {
  models: ModelPreferences;
}

/** 系统级 RAGFlow 连接设置（**不含密钥**——密钥统一走系统密钥清单）。 */
export interface RagflowSettings {
  baseUrl: string;
  enabled: boolean;
  enabledSource: SettingValueSource;
  baseUrlSource: SettingValueSource;
  /** 检索参数：库里配置优先，未配置时回落内置默认值并在此展示 */
  similarityThreshold: number;
  topK: number;
  /**
   * 报告侧检索使用的 dataset 映射，形如 `{"history":["<dataset_id>"]}`。
   * 空串表示未配置任何 dataset（此时报告侧检索不会命中）。
   */
  datasetsJson: string;
  /** 检索请求超时（秒），库里未配置时回落内置默认值 */
  timeoutSeconds: number;
  /** 触发服务端解析的超时（秒），库里未配置时回落内置默认值 */
  parseTimeoutSeconds: number;
  /** 同一文档最多注入的片段数，库里未配置时回落内置默认值 */
  maxChunksPerDocument: number;
  /** 启用 RAGFlow 知识增强的报告章节（逗号分隔），库里未配置时回落内置默认值 */
  enabledSections: string;
}

/** 设置页一次性拉取的完整视图 */
export interface SettingsOverviewResponse {
  preferences: UserPreferences;
  /**
   * 系统级 RAGFlow 设置；**非管理员为 null**。
   *
   * 后端按身份分层：只有管理员才拿得到这一段（含 Base URL、启用状态、密钥掩码与尾串）。
   * 普通用户**使用** RAGFlow 检索走的是服务端链路，与本接口无关 —— 所以这里为 null
   * 不代表检索不可用，只代表"这段配置不对你开放"。
   */
  ragflow: RagflowSettings | null;
}

export interface UpdatePreferencesRequest {
  models?: {
    /** 省略 / null = 不改；空串 = 清空 */
    selected?: string | null;
    reranker?: string | null;
  };
}

/**
 * 系统级 RAGFlow 非密钥设置更新请求。
 *
 * 密钥（API Key）统一走通用系统密钥端点 `PUT/DELETE /settings/secrets/{key}`，
 * 不在本请求里出现，避免两套密钥写入路径并存。
 *
 * `baseUrl` 传空串表示"撤销库内覆盖、回落内置默认值"。
 */
export interface UpdateRagflowRequest {
  baseUrl?: string;
  enabled?: boolean;
  /** 形如 {"history":["<dataset_id>"]}；空串表示撤销库内覆盖 */
  datasetsJson?: string;
  /** 0.0 ~ 1.0 */
  similarityThreshold?: number;
  /** 1 ~ 20 */
  topK?: number;
  /** 检索请求超时（秒）0 < t <= 600；传 null 表示撤销库内覆盖 */
  timeoutSeconds?: number;
  /** 触发服务端解析的超时（秒）0 < t <= 600；传 null 表示撤销库内覆盖 */
  parseTimeoutSeconds?: number;
  /** 同一文档最多注入的片段数 1 ~ 50；传 null 表示撤销库内覆盖 */
  maxChunksPerDocument?: number;
  /** 启用 RAGFlow 知识增强的报告章节（逗号分隔）；空串表示撤销库内覆盖 */
  enabledSections?: string;
}

export interface RagflowConnectionTestResponse {
  ok: boolean;
  message: string;
  datasetCount: number;
}

/** 当前 RAGFlow 连接下的一个知识库（供设置页选择，不含敏感信息） */
export interface RagflowDatasetSummary {
  id: string;
  name: string;
  documentCount: number;
  chunkCount: number;
}

/**
 * 知识库列表视图。
 *
 * `ok=false` 表示**没取到**列表，`message` 说明原因（未启用 / 未配置凭据 / 连不上 / 无权限）。
 * 这与"连接正常但确实没有知识库"是两种不同情况，UI 要分开提示。
 */
export interface RagflowDatasetListResponse {
  ok: boolean;
  message: string;
  datasets: RagflowDatasetSummary[];
}

/** 通用系统密钥的可展示信息（无明文） */
export interface SystemSecret {
  key: string;
  label: string;
  description: string;
  /** 密钥种类：api_key / oauth2 / generic_token，前端按此分发渲染 */
  kind: string;
  configured: boolean;
  /** 掩码串；未配置时为空串 */
  maskedValue: string;
  /** 掩码尾串；明文过短时为 null */
  hint: string | null;
  /** 当前生效来源：system / env / none */
  source: SecretSource;
  /** 最后更新时间，ISO 字符串 */
  updatedAt: string | null;
}

/** 系统密钥列表 */
export interface SystemSecretList {
  secrets: SystemSecret[];
}
