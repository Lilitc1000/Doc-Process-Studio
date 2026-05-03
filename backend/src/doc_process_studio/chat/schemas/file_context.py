from pydantic import BaseModel, Field

from .attachment import ChatAttachment


class UploadedFileContext(BaseModel):
    filename: str = Field(..., description="上传文件名")
    content_type: str | None = Field(
        default=None,
        description="上传文件的 MIME 类型",
    )
    content: str = Field(..., description="提取出的文件内容")


class PreparedUploadedFile(BaseModel):
    attachment: ChatAttachment = Field(..., description="已持久化的附件信息")
    context: UploadedFileContext = Field(..., description="提取出的文件上下文")
