from pydantic import BaseModel, Field, ConfigDict


class Connection(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    type: str
    direction: str

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True
    )
