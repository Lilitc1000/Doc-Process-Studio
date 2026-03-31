from pydantic import BaseModel, Field


class UploadedFileContext(BaseModel):
    filename: str = Field(..., description="上传文件名")
    content_type: str | None = Field(
        default=None,
        description="上传文件的 MIME 类型",
    )
    content: str = Field(..., description="提取出的文件内容")
