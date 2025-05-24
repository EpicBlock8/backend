from .base import BaseRequest

class RegisterAccount(BaseRequest):
    username: str
    public_key: str
