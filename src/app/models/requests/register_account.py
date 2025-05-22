from pydantic import BaseModel


class RegisterAccount(BaseModel):
    username: str
    public_key: bytes
