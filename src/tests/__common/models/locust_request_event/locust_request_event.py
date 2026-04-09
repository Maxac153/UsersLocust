from typing import Any

from pydantic import BaseModel


class LocustRequestEvent(BaseModel):
    request_type: str = "TRANSACTION"
    name: str
    response_time: int  # ms
    response_length: int = 0
    exception: Any | None = None
