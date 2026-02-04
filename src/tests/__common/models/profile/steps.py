from pydantic import BaseModel


class Step(BaseModel):
    TPS: float
    RAMP_TIME: int
    HOLD_TIME: int
