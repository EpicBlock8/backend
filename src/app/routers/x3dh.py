from base64 import b64decode, b64encode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.models.requests import SignedPayload
from app.models.requests.x3dh import (
    GetPrekeyBundleRequest,
    GrabReturnMessages,
    PostReturnMessage,
    PostReturnMessageResponse,
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
async def signed_prekey_push(data: SignedPrekeyPush = Depends(SignedPayload.unwrap(SignedPrekeyPush))):
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
            prekey_bundle.prekey = b64decode(data.signed_prekey_public)
            prekey_bundle.sig_prekey = b64decode(data.signed_prekey_signature)
        else:
            # Create new prekey bundle
            prekey_bundle = PrekeyBundle(
                f_username=data.username,
                prekey=b64decode(data.signed_prekey_public),
                sig_prekey=b64decode(data.signed_prekey_signature),
            )
        session.add(prekey_bundle)
        session.commit()
        session.refresh(prekey_bundle)

    return JSONResponse(content={"message": "Signed prekey push received"})


@router.post("/x3dh/otp_prekey_push")
async def otp_prekey_push(data: OtpPrekeyPush = Depends(SignedPayload.unwrap(OtpPrekeyPush))):
    logger.debug(data)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(
                status_code=404, detail="User not found"
            )  # double checking in case -

        for otp_key in data.pub_otps:
            new_otp = Otp(f_username=data.username, otp_val=b64decode(otp_key))
            session.add(new_otp)

        session.commit()

    return JSONResponse(content={"message": "OTP prekey push received"})


@router.post("/x3dh/prekey_bundle", response_model=PrekeyBundleResponse)
async def get_prekey_bundle(data: GetPrekeyBundleRequest = Depends(SignedPayload.unwrap(GetPrekeyBundleRequest))):
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
            .where(Otp.f_username == data.target_username, Otp.used == False)
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
            identity_key=b64encode(user.public_key).decode("utf8"),
            signed_prekey=b64encode(prekey_bundle_db.prekey).decode("utf8"),
            signed_prekey_signature=b64encode(prekey_bundle_db.sig_prekey).decode("utf8"),
            one_time_prekey=b64encode(one_time_prekey_val).decode("utf8"),
        )

@router.post("/x3dh/post_return_message", response_model=PostReturnMessageResponse)
async def post_return_messages(
    data: PostReturnMessage = Depends(SignedPayload.unwrap(PostReturnMessage)),
):
    with Session(engine) as session:
        # Verify user exists
        sharer = session.exec(
            select(User).where(User.username == data.sharer_username)
        ).first()
        
        if not sharer:
            raise HTTPException(
                status_code=404, detail=f"Sharer {data.sharer_username} not found" 
            )

        # Verify recipient exists
        recipient = session.exec(
            select(User).where(User.username == data.recipient_username)
        ).first()
        
        if not recipient:
            raise HTTPException(
                status_code=404, detail=f"Recipient {data.recipient_username} not found"
            )
        
        # Store the initial message for the recipient        
        new_message = MessageStore(
            recipient_username=data.recipient_username,
            sharer_identity_key_public=b64decode(data.sharer_identity_key_public),
            eph_key=b64decode(data.sharer_ephemeral_key_public),
            sharer_username=data.sharer_username,
            otp_hash=b64decode(data.otp_hash),
            e_message=b64decode(data.encrypted_message),
        )

        session.add(new_message)
        session.commit()

        logger.info(
            "Initial message stored for %s from %s", data.recipient_username, data.sharer_username
        )
        
        return PostReturnMessageResponse(message="Message posted successfully")



@router.post(
    "/x3dh/grab_return_messages", response_model=GrabReturnMessages
) 
async def grab_return_messages(
    data: GrabReturnMessagesRequest = Depends(SignedPayload.unwrap(GrabReturnMessagesRequest)),
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
            select(MessageStore).where(MessageStore.recipient_username == data.username)
        ).all()

        if not message_records:
            logger.info("No initial messages found for user: %s", data.username)
            return GrabReturnMessages(messages=[])

        return_messages = []
        for record in message_records:
            return_messages.append(
                ReturnMessage(
                    sharer_identity_key_public=b64encode(record.sharer_identity_key_public).decode("utf8"),
                    sharer_ephemeral_key_public=b64encode(record.eph_key).decode("utf8"),
                    sharer_username=record.sharer_username,
                    otp_hash=b64encode(record.otp_hash).decode("utf8"),  # sha-256 hash of the otp
                    encrypted_message=b64encode(record.e_message).decode("utf8"),
                )
            )
            # Delete the message from the server after fetching
            session.delete(record)

        session.commit()
        logger.info(
            "Retrieved and deleted %s initial messages for user: %s", len(return_messages), data.username
        )

        return GrabReturnMessages(messages=return_messages)
