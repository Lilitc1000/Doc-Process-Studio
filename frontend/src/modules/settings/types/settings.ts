/**
 * 设置模块类型定义。
 *
 * 契约提醒：后端 API 一律 **snake_case**，由 `@shared/api/request` 的 axios 拦截器
 * （humps）自动转换，所以这里写 camelCase 即可。
 *
 * 安全约定：**任何类型里都不存在"明文密钥"字段**。后端只在保存时接收明文，
 * 读取时永远只返回 `maskedApiKey`（掩码）+ `configured`（是否已配置）+
 * `hint`（尾 4 位，明文过短时为 null）。眼睛图标只作用于用户**正在输入**的内容。
 */

/** 凭据当前来源：system=管理员在设置页写入的共享密钥，env=环境变量兜底，none=未配置 */
export type SecretSource = 'system' | 'env' | 'none';

/** 配置项来源：system=库里配置，env=环境变量兜底 */
export type SettingValueSource = 'system' | 'env';

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

/** 系统级 RAGFlow 凭据的**可展示信息**（无明文） */
export interface RagflowCredential {
  configured: boolean;
  /** 掩码串，如 `••••••••Y30tkYQ`；未配置时为固定掩码 */
  maskedApiKey: string;
  /** 掩码尾串；明文过短时为 null（只显示固定掩码，避免掩码本身泄露内容） */
  hint: string | null;
  source: SecretSource;
  /** 密钥最后更新时间，ISO 字符串 */
  updatedAt: string | null;
}

export interface RagflowSettings {
  baseUrl: string;
  enabled: boolean;
  enabledSource: SettingValueSource;
  baseUrlSource: SettingValueSource;
  credential: RagflowCredential;
  /** 检索参数：库里配置优先，未配置时回落环境变量并在此展示 */
  similarityThreshold: number;
  topK: number;
  /**
   * 报告侧检索使用的 dataset 映射，形如 `{"history":["<dataset_id>"]}`。
   * 空串表示未配置任何 dataset（此时报告侧检索不会命中）。
   */
  datasetsJson: string;
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
 * 系统级 RAGFlow 设置更新请求。
 *
 * `apiKey` 的四种语义（后端定死，前端必须遵守）：
 *
 * | 传值                | 行为                       |
 * | ------------------- | -------------------------- |
 * | 字段不传            | 保持不变                   |
 * | `''` 空串           | 保持不变（防误清）         |
 * | 非空字符串          | 加密后覆盖                 |
 * | 调 clearRagflowApiKey | 清除                     |
 *
 * `baseUrl` 则相反：传空串表示"撤销库内覆盖、回落环境变量兜底"。
 */
export interface UpdateRagflowRequest {
  baseUrl?: string;
  enabled?: boolean;
  apiKey?: string;
  /** 形如 {"history":["<dataset_id>"]}；空串表示撤销库内覆盖 */
  datasetsJson?: string;
  /** 0.0 ~ 1.0 */
  similarityThreshold?: number;
  /** 1 ~ 20 */
  topK?: number;
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
