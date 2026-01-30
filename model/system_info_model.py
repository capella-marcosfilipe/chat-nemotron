from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    available_modes: dict[str, bool]
    default_mode: str
