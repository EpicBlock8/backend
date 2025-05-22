from pydantic import BaseModel


class DownloadFile(BaseModel):
    uuid: str


