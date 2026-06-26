from pydantic import BaseModel, ConfigDict


class UpstreamOllamaModelRecord(BaseModel):
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
