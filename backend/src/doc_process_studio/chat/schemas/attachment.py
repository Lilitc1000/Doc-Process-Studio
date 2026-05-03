from datetime import datetime

from pydantic import BaseModel, Field


class ChatAttachment(BaseModel):
    attachment_id: str = Field(
        ...,
        description="前端下载时使用的附件标识",
    )
    name: str = Field(..., description="前端展示附件文件名")
    source: str = Field(..., description="附件来源，如 uploaded/generated")
    mime_type: str = Field(
        ...,
        description="文件 MIME 类型",
    )
    size_bytes: int = Field(
        ...,
        description="文件大小，单位字节",
    )
    size_label: str = Field(
        ...,
        description="供前端展示的文件大小文本",
    )
    download_url: str = Field(
        ...,
        description="受控附件下载地址",
    )
    expires_at: datetime = Field(
        ...,
        description="文件过期时间",
    )


class ChatAttachmentMetadata(BaseModel):
    attachment_id: str = Field(
        ...,
        description="附件唯一标识",
    )
    conversation_id: str = Field(..., description="所属会话标识")
    skill_id: str = Field(..., description="所属 skill 标识")
    source: str = Field(..., description="附件来源，如 uploaded/generated")
    content_hash: str | None = Field(
        default=None,
        description="附件内容哈希，用于同会话内复用相同上传文件",
    )
    name: str = Field(..., description="附件文件名")
    mime_type: str = Field(..., description="附件 MIME 类型")
    size_bytes: int = Field(..., description="附件大小")
    created_at: datetime = Field(..., description="创建时间")
    expires_at: datetime = Field(..., description="过期时间")
