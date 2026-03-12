from pydantic import BaseModel


class GenericMessageResponse(BaseModel):
    message: str
