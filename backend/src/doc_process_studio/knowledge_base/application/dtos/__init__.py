from pydantic import BaseModel, Field


class KBChunkPayload(BaseModel):
    project_name: str = Field(..., description="所属项目名")
    document_id: str = Field(..., description="文档 ID")
    file_name: str = Field(..., description="原始文件名")
    file_path: str = Field(default="", description="文件夹路径")
    file_type: str = Field(..., description="文件类型")
    version: int = Field(default=1, description="版本号")
    is_latest: bool = Field(default=True, description="是否最新版")
    page_number: int | None = Field(default=None, description="页码（PDF）")
    section_title: str | None = Field(default=None, description="章节标题")
    sheet_name: str | None = Field(default=None, description="Sheet 名称（Excel）")
    content_type: str = Field(default="text", description="内容类型：text/table/ocr")
    chunk_index: int = Field(default=0, description="块内序号")
    content: str = Field(..., description="文本内容")
    uploaded_at: str = Field(default="", description="上传时间")


class KBProjectDTO(BaseModel):
    id: str
    name: str
    description: str | None = None
    folder_count: int = 0
    document_count: int = 0
    is_updating: bool = False
    last_updated_at: str | None = None
    created_at: str
    updated_at: str


class KBFolderDTO(BaseModel):
    id: str
    project_id: str
    parent_id: str | None = None
    name: str
    path: str
    sort_order: int = 0
    created_at: str
    updated_at: str


class KBDocumentDTO(BaseModel):
    id: str
    project_id: str
    folder_id: str | None = None
    file_name: str
    file_type: str
    file_size: int = 0
    chunk_count: int = 0
    version: int = 1
    is_indexed: bool = False
    is_latest: bool = True
    uploaded_at: str


class KBProjectSimpleItemDTO(BaseModel):
    id: str
    name: str


__all__ = [
    "KBChunkPayload",
    "KBDocumentDTO",
    "KBFolderDTO",
    "KBProjectDTO",
    "KBProjectSimpleItemDTO",
]
