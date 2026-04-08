from pydantic import BaseModel, Field


class SkillToolAttachmentConfig(BaseModel):
    mime_type: str = Field(..., description="产物 MIME 类型")
    default_name_template: str = Field(
        default="{tool_name}-output.bin",
        description="默认输出文件名模板",
    )


class SkillToolArgBinding(BaseModel):
    flag: str = Field(..., description="命令列参数名，例如 --output")
    serializer: str = Field(
        default="string",
        description="参数序列化方式，如 string/json_file/attachment_output_name",
    )
    text_normalizer: str | None = Field(
        default=None,
        description="当 serializer=json_file 且模型传入字符串时，可选的文本规整策略",
    )


class SkillToolExecutionConfig(BaseModel):
    runtime: str = Field(default="python", description="脚本执行运行时")
    fixed_args: list[str] = Field(
        default_factory=list,
        description="执行时始终附加的固定参数",
    )
    arg_bindings: dict[str, SkillToolArgBinding] = Field(
        default_factory=dict,
        description="工具入参与脚本参数的映射关系",
    )
    attachment: SkillToolAttachmentConfig | None = Field(
        default=None,
        description="若该工具会生成文件附件，则声明其输出配置",
    )


class SkillToolStatusConfig(BaseModel):
    label: str | None = Field(
        default=None,
        description="前端展示用的业务标签，例如 生成文档文件",
    )
    start: str | None = Field(
        default=None,
        description="工具开始执行时的业务化状态文案",
    )
    success: str | None = Field(
        default=None,
        description="工具执行成功时的业务化状态文案",
    )
    failure: str | None = Field(
        default=None,
        description="工具执行失败时的业务化状态文案",
    )


class SkillToolConfig(BaseModel):
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具说明")
    kind: str = Field(default="script", description="工具类型")
    path: str = Field(..., description="skill 内相对路径")
    parameters: dict = Field(..., description="OpenAI tool JSON Schema")
    execution: SkillToolExecutionConfig = Field(..., description="执行配置")
    status: SkillToolStatusConfig | None = Field(
        default=None,
        description="工具状态文案配置",
    )


class SkillInterfaceConfig(BaseModel):
    id: str = Field(..., description="skill 唯一标识")
    display_name: str = Field(..., description="用于前端显示的名称")
    short_description: str = Field(
        default="",
        description="skill 简短说明",
    )
    default_prompt: str = Field(..., description="默认注入提示词")
    tools: list[SkillToolConfig] = Field(
        default_factory=list,
        description="当前 skill 声明的可执行工具",
    )


class SkillListResponse(BaseModel):
    skills: list[SkillInterfaceConfig] = Field(
        default_factory=list,
        description="当前可用的 skill 列表",
    )
    default_skill_id: str = Field(
        ...,
        description="默认选中的 skill 标识",
    )


class SkillContextSearchResponse(BaseModel):
    skill_id: str = Field(..., description="skill 标识")
    query: str = Field(..., description="检索关键词")
    chunks: list[dict[str, str]] = Field(
        default_factory=list,
        description="命中的 skill 片段",
    )


class SkillCacheStatusResponse(BaseModel):
    ok: bool = Field(..., description="Redis 是否可用")
    message: str = Field(..., description="状态消息")


class SkillConversationCacheResponse(BaseModel):
    conversation_id: str = Field(..., description="会话标识")
    exists: bool = Field(..., description="Redis 中是否存在该会话状态")
    ttl_seconds: int = Field(..., description="当前剩余 TTL 秒数")
    message: str = Field(..., description="状态说明")
