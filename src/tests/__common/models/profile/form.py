from pydantic import BaseModel


class Form(BaseModel):
    x: int
    y: int
    width: int
    height: int
