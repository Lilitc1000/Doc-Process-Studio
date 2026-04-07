from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field


class ChatAttachment(BaseModel):
    attachment_id: str = Field(
        ...,
        description="前端下载时使用的附件标识",
        validation_alias=AliasChoices("attachment_id", "attachmentId"),
        serialization_alias="attachmentId",
    )
    name: str = Field(..., description="前端展示附件文件名")
    source: str = Field(..., description="附件来源，如 uploaded/generated")
    mime_type: str = Field(
        ...,
        description="文件 MIME 类型",
        validation_alias=AliasChoices("mime_type", "mimeType"),
        serialization_alias="mimeType",
    )
    size_bytes: int = Field(
        ...,
        description="文件大小，单位字节",
        validation_alias=AliasChoices("size_bytes", "sizeBytes"),
        serialization_alias="sizeBytes",
    )
    size_label: str = Field(
        ...,
        description="供前端展示的文件大小文本",
        validation_alias=AliasChoices("size_label", "sizeLabel"),
        serialization_alias="sizeLabel",
    )
    download_url: str = Field(
        ...,
        description="受控附件下载地址",
        validation_alias=AliasChoices("download_url", "downloadUrl"),
        serialization_alias="downloadUrl",
    )
    expires_at: datetime = Field(
        ...,
        description="文件过期时间",
        validation_alias=AliasChoices("expires_at", "expiresAt"),
        serialization_alias="expiresAt",
    )


class ChatAttachmentMetadata(BaseModel):
    attachment_id: str = Field(
        ...,
        description="附件唯一标识",
        validation_alias=AliasChoices("attachment_id", "attachmentId"),
        serialization_alias="attachmentId",
    )
    conversation_id: str = Field(..., description="所属会话标识")
    skill_id: str = Field(..., description="所属 skill 标识")
    source: str = Field(..., description="附件来源，如 uploaded/generated")
    name: str = Field(..., description="附件文件名")
    mime_type: str = Field(..., description="文件 MIME 类型")
    size_bytes: int = Field(..., description="文件大小")
    created_at: datetime = Field(..., description="创建时间")
    expires_at: datetime = Field(..., description="过期时间")
