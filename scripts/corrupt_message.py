import os

from sqlalchemy import Engine
from sqlmodel import Session, create_engine, select

from app.models.schema import MessageStore
from app.shared import load_config

config = load_config()


def attack_message_store(engine: Engine, recipient: str):
    with Session(engine) as session:
        msg = session.exec(
            select(MessageStore).where(MessageStore.recipient_username == recipient)
        ).first()
        if not msg:
            print(f"[!] No message found for recipient '{recipient}'")
            return

        msg.e_message = os.urandom(128)
        msg.eph_key = os.urandom(32)
        session.add(msg)
        session.commit()
        print(f"[✔] Tampered message content for recipient '{recipient}'")


if __name__ == "__main__":
    import argparse

    from app.shared.db import engine

    def parse_args():
        parser = argparse.ArgumentParser(description="Simulate message tampering")
        parser.add_argument("recipient", type=str, help="Recipient username")
        parser.add_argument("--db", type=str, help="SQLite database path override")
        return parser.parse_args()

    args = parse_args()
    if args.db:
        engine = create_engine(args.db)

    attack_message_store(engine, args.recipient)
