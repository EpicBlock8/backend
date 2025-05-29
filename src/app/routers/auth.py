import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.models.requests import SignedPayload
from app.models.requests.register_account import RegisterAccount
from app.models.schema import User
from app.shared import Logger, load_config
from app.shared.db import engine

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint

@router.post("/auth/register")
async def register(
    data: Annotated[
        RegisterAccount, Depends(SignedPayload.unwrap_no_checks(RegisterAccount))
    ],
):
    """
    input: master password
    derive: master chief using argon2id
    key generation identity kek key pair
    encrypt private identity kek using master chief
    push
    {username, i_kek_public} - signed with i_kek_private <- ignoring signature for now
    ==========================
    verify signature
    check if username is unique -> reject if not 403 not authorised
    persist to db
    """
    logger.debug(data)

    with Session(engine) as session:
        # Check if username is unique
        existing_user = session.exec(
            select(User).where(User.username == data.username)
        ).first()
        if existing_user:
            raise HTTPException(status_code=403, detail="Username already exists")

        # Persist to db
        # Assuming RegisterAccount has 'username' and 'public_key' attributes
        # based on the schema.py and common practice.
        public_key_bytes = base64.b64decode(data.public_key)
        new_user = User(username=data.username, public_key=public_key_bytes)
        session.add(new_user)
        session.commit()
        session.refresh(new_user)

    return JSONResponse(
        content={"message": "User registered successfully", "user_id": new_user.id}
    )
