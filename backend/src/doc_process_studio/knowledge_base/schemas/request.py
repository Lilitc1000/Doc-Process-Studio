from pydantic import BaseModel, Field


class KBProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="项目名称")
    description: str = Field(default="", max_length=1024, description="项目描述")


class KBProjectRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="新项目名称")


class KBFolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="文件夹名称")
    parent_id: str | None = Field(default=None, description="父文件夹 ID，为空则创建在项目根目录")


class KBFolderRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="新文件夹名称")
