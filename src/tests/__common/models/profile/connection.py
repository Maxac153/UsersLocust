from pydantic import BaseModel, Field


class Connection(BaseModel):
    FROM_: str = Field(..., alias="FROM")
    TO: str
    TYPE: str
    DIRECTION: str
