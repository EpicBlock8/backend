from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, create_engine, select

from app.models.requests import SignedPayload
from app.models.requests.x3dh import (
    GetPrekeyBundleRequest,
    GrabReturnMessages,
    ReturnMessage,
    OtpPrekeyPush,
    PrekeyBundleResponse,
    SignedPrekeyPush,
    GrabReturnMessagesRequest,
)
from app.models.schema import MessageStore, Otp, PrekeyBundle, User
from app.shared import Logger, load_config
from app.shared.db import engine
logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint

# TODO: make pq, and see if there is a way to do limited client-syncing


@router.post("/x3dh/signed_prekey_push")
async def signed_prekey_push(data=Depends(SignedPayload.unwrap(SignedPrekeyPush))):
    logger.debug(data)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        prekey_bundle = session.exec(
            select(PrekeyBundle).where(PrekeyBundle.f_username == data.username)
        ).first()
        if prekey_bundle:
            # Update existing prekey bundle
            prekey_bundle.prekey = data.signed_prekey_public
            prekey_bundle.sig_prekey = data.signed_prekey_signature
        else:
            # Create new prekey bundle
            prekey_bundle = PrekeyBundle(
                f_username=data.username,
                prekey=data.signed_prekey_public,
                sig_prekey=data.signed_prekey_signature,
            )
        session.add(prekey_bundle)
        session.commit()
        session.refresh(prekey_bundle)

    return JSONResponse(content={"message": "Signed prekey push received"})


@router.post("/x3dh/otp_prekey_push")
async def otp_prekey_push(data=Depends(SignedPayload.unwrap(OtpPrekeyPush))):
    logger.debug(data)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(
                status_code=404, detail="User not found"
            )  # double checking in case -

        for otp_key in data.pub_otps:
            new_otp = Otp(f_username=data.username, otp_val=otp_key)
            session.add(new_otp)

        session.commit()

    return JSONResponse(content={"message": "OTP prekey push received"})


@router.post("/x3dh/prekey_bundle", response_model=PrekeyBundleResponse)
async def get_prekey_bundle(data=Depends(SignedPayload.unwrap(GetPrekeyBundleRequest))):
    logger.debug("Fetching prekey bundle for user: %s", data.target_username)
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == data.target_username)
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        prekey_bundle_db = session.exec(
            select(PrekeyBundle).where(PrekeyBundle.f_username == data.target_username)
        ).first()
        if not prekey_bundle_db:
            raise HTTPException(
                status_code=404, detail="Prekey bundle not found for user"
            )

        # Fetch an unused OTP with row-level locking to prevent race conditions
        otp_record = session.exec(
            select(Otp)
            .where(Otp.f_username == data.target_username, Otp.used is False)
            .with_for_update()
        ).first()

        one_time_prekey_val = None
        if otp_record:
            one_time_prekey_val = otp_record.otp_val
            otp_record.used = True
            session.add(otp_record)
            session.commit()
            session.refresh(otp_record)
            logger.info(
                "OTP %s for user %s marked as used.", otp_record.id, data.target_username
            )
        else:
            # OTP is mandatory, raise an error if not found
            logger.error(
                "Mandatory OTP not available for user: %s", data.target_username
            )
            raise HTTPException(
                status_code=404,
                detail="Mandatory OTP not available for user: %s" % data.target_username,
            )

        return PrekeyBundleResponse(
            identity_key=user.public_key,
            signed_prekey=prekey_bundle_db.prekey,
            signed_prekey_signature=prekey_bundle_db.sig_prekey,
            one_time_prekey=one_time_prekey_val,
        )


@router.post(
    "/x3dh/grab_return_messages", response_model=GrabReturnMessages
) 
async def grab_return_messages(
    data=Depends(SignedPayload.unwrap(GrabReturnMessagesRequest)),
):
    logger.debug("Grabbing initial messages for user: %s", data.username)
    with Session(engine) as session:
        # Verify user exists
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User {data.username} not found"
            )

        # Fetch all messages for the user
        message_records = session.exec(
            select(MessageStore).where(MessageStore.f_username == data.username)
        ).all()

        if not message_records:
            logger.info("No initial messages found for user: %s", data.username)
            return GrabReturnMessages(messages=[])

        return_messages = []
        for record in message_records:
            return_messages.append(
                ReturnMessage(
                    sharer_identity_key_public=record.sharer_identity_key_public,
                    sharer_ephemeral_key_public=record.eph_key,
                    otp_hash=record.otp_hash,  # sha-256 hash of the otp
                    encrypted_dek=record.e_dek,
                )
            )
            # Delete the message from the server after fetching
            session.delete(record)

        session.commit()
        logger.info(
            "Retrieved and deleted %s initial messages for user: %s", len(return_messages), data.username
        )

        return GrabReturnMessages(messages=return_messages)
