from .serde_base import SerdeBase


class RegisterAccount(SerdeBase):
    username: str
    public_key: str
