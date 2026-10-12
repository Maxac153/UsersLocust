from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class Step(BaseModel):
    TPS: Annotated[float, Field(gt=0, description="Target transactions per second")]
    RAMP_TIME: Annotated[float, Field(ge=0, description="Ramp to target TPS, minutes")]
    HOLD_TIME: Annotated[float, Field(ge=0, description="Hold target TPS, minutes")]

    @model_validator(mode="after")
    def check_not_empty(self) -> "Step":
        if self.RAMP_TIME + self.HOLD_TIME <= 0:
            raise ValueError("RAMP_TIME + HOLD_TIME Must Be Greater Than 0")
        return self
