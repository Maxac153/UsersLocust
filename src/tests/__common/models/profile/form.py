from pydantic import BaseModel


class Form(BaseModel):
    X: int
    Y: int
    WIDTH: int
    HEIGHT: int
