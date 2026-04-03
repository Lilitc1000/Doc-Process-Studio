from pydantic import BaseModel, ConfigDict, Field


class UpstreamOllamaModelRecord(BaseModel):
    # 兼容不同上游返回结构：
    # 有些接口使用 name，有些用 model 或 id。
    name: str | None = None
    model: str | None = None
    id: str | None = None

    model_config = ConfigDict(extra="ignore")

    def resolved_name(self) -> str | None:
        for candidate in (self.name, self.model, self.id):
            if isinstance(candidate, str):
                normalized_name = candidate.strip()
                if normalized_name:
                    return normalized_name
        return None


class OllamaModelItem(BaseModel):
    name: str = Field(..., description="模型名称")


class OllamaModelListResponse(BaseModel):
    models: list[OllamaModelItem] = Field(
        default_factory=list,
        description="可用模型列表",
    )
