from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field


class ChatSessionAttachment(BaseModel):
    name: str = Field(..., description="附件名称")
    source: str | None = Field(
        default=None,
        description="附件来源，如 uploaded/generated",
    )
    size_label: str = Field(
        ...,
        description="附件大小显示文本",
        validation_alias=AliasChoices("size_label", "sizeLabel"),
        serialization_alias="sizeLabel",
    )
    attachment_id: str | None = Field(
        default=None,
        description="可下载附件标识",
        validation_alias=AliasChoices("attachment_id", "attachmentId"),
        serialization_alias="attachmentId",
    )
    download_url: str | None = Field(
        default=None,
        description="下载地址",
        validation_alias=AliasChoices("download_url", "downloadUrl"),
        serialization_alias="downloadUrl",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="过期时间",
        validation_alias=AliasChoices("expires_at", "expiresAt"),
        serialization_alias="expiresAt",
    )
    mime_type: str | None = Field(
        default=None,
        description="文件 MIME 类型",
        validation_alias=AliasChoices("mime_type", "mimeType"),
        serialization_alias="mimeType",
    )


class ChatSessionMessageNode(BaseModel):
    id: str = Field(..., description="消息节点标识")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息文本")
    api_content: str | None = Field(default=None, description="发送给模型的内容")
    files: list[ChatSessionAttachment] = Field(
        default_factory=list,
        description="仅用于展示的附件信息",
    )
    tool_statuses: list[dict[str, str | None]] = Field(
        default_factory=list,
        description="工具调用状态记录",
    )
    timestamp: datetime = Field(..., description="消息时间")
    parent_id: str | None = Field(default=None, description="父消息标识")
    child_ids: list[str] = Field(default_factory=list, description="子消息标识")


class ChatSessionSnapshot(BaseModel):
    message_nodes: list[ChatSessionMessageNode] = Field(
        default_factory=list,
        description="完整消息树节点",
    )
    root_child_ids: list[str] = Field(
        default_factory=list,
        description="根节点消息列表",
    )
    selected_root_child_id: str | None = Field(
        default=None,
        description="当前选中的根节点消息",
    )
    selected_child_id_by_parent: dict[str, str] = Field(
        default_factory=dict,
        description="各父节点当前选中的子节点",
    )
    selected_processing_mode: str = Field(..., description="当前 skill 标识")
    selected_model: str = Field(..., description="当前模型名称")


class ChatSessionSummary(BaseModel):
    id: str = Field(..., description="会话标识")
    title: str = Field(..., description="会话标题")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    selected_processing_mode: str = Field(..., description="当前 skill 标识")
    selected_model: str = Field(..., description="当前模型名称")


class ChatSessionDetail(ChatSessionSummary):
    snapshot: ChatSessionSnapshot = Field(..., description="会话快照")


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionSummary] = Field(
        default_factory=list,
        description="历史会话列表",
    )


class ChatSessionUpsertRequest(BaseModel):
    title: str = Field(default="", description="会话标题")
    title_source_messages: list[str] = Field(
        default_factory=list,
        description="用于自动生成标题的消息片段",
    )
    snapshot: ChatSessionSnapshot = Field(..., description="会话快照")


class ChatSessionTitleUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, description="新的会话标题")
