import os

from sqlalchemy import Engine
from sqlmodel import Session, create_engine, select

from app.models.schema import PrekeyBundle
from app.shared import load_config

config = load_config()


def attack_prekey_bundle(engine: Engine, username: str):
    with Session(engine) as session:
        prekey = session.exec(
            select(PrekeyBundle).where(PrekeyBundle.f_username == username)
        ).first()
        if not prekey:
            print(f"[!] No prekey bundle for user '{username}'")
            return

        prekey.prekey = os.urandom(32)
        prekey.sig_prekey = os.urandom(64)
        session.add(prekey)
        session.commit()
        print(f"[✔] Tampered prekey bundle for user '{username}'")


if __name__ == "__main__":
    import argparse

    from app.shared.db import engine

    def parse_args():
        parser = argparse.ArgumentParser(description="Simulate prekey bundle tampering")
        parser.add_argument("username", type=str, help="Username to modify")
        parser.add_argument("--db", type=str, help="SQLite database path override")
        return parser.parse_args()

    args = parse_args()
    if args.db:
        engine = create_engine(args.db)

    attack_prekey_bundle(engine, args.username)
