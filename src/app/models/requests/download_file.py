from pydantic import BaseModel

"""
download_file
sending UUID
===============
verify signature
verify ability to access (are they owner / has it been shared?)
send encrypted file body.
================
decrypt DEK
decrypt body
"""

class DownloadFile(BaseModel):
    uuid: str
    signature: bytes

