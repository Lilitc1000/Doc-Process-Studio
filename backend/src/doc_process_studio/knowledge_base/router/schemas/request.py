from pydantic import BaseModel, Field


class KBProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="项目名称（在 RAGFlow 建同名 dataset）")
    description: str = Field(default="", max_length=1024, description="项目描述")


class KBProjectRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="新项目名称")


__all__ = [
    "KBProjectCreateRequest",
    "KBProjectRenameRequest",
]
