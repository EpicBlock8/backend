import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, create_engine, select

from app.models.requests.register_account import RegisterAccount
from app.models.schema import User
from app.shared import Logger, load_config

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint
engine = create_engine(config.database.path)


@router.get("/auth/register")
def register(data: RegisterAccount = Depends()):
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

    data = data.model_copy()
    logger.debug(data)

    with Session(engine) as session:
        # Check if username is unique
        existing_user = session.exec(select(User).where(User.username == data.username)).first()
        if existing_user:
            raise HTTPException(status_code=403, detail="Username already exists")

        # Persist to db
        # Assuming RegisterAccount has 'username' and 'public_key' attributes
        # based on the schema.py and common practice.
        new_user = User(username=data.username, public_key=data.public_key)
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return {"message": "User registered successfully", "user_id": new_user.id}




