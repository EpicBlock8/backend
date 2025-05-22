from pydantic import BaseModel


class DownloadFileRequest(BaseModel):
    uuid: str


