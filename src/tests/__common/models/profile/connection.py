from pydantic import BaseModel, Field


class Connection(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    type: str
    direction: str
