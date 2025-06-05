from sqlalchemy import Engine
from sqlmodel import Session, create_engine, select

from app.models.schema import FileShare
from app.shared import load_config

config = load_config()


def toggle_share_revocation(engine: Engine, recipient: str):
    with Session(engine) as session:
        share = session.exec(
            select(FileShare).where(FileShare.recipient_username == recipient)
        ).first()
        if not share:
            print(f"[!] No file share found for recipient '{recipient}'")
            return

        share.revoked = not share.revoked
        session.add(share)
        session.commit()
        print(f"[✔] Toggled share revocation for recipient '{recipient}'")


if __name__ == "__main__":
    import argparse

    from app.shared.db import engine

    def parse_args():
        parser = argparse.ArgumentParser(
            description="Simulate file share revocation toggle"
        )
        parser.add_argument("recipient", type=str, help="Recipient username")
        parser.add_argument("--db", type=str, help="SQLite database path override")
        return parser.parse_args()

    args = parse_args()
    if args.db:
        engine = create_engine(args.db)

    toggle_share_revocation(engine, args.recipient)
