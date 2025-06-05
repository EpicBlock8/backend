import os

from sqlalchemy import Engine
from sqlmodel import Session, create_engine, select

from app.models.schema import Otp
from app.shared import load_config

config = load_config()


def attack_otp(engine: Engine, username: str):
    with Session(engine) as session:
        otp = session.exec(select(Otp).where(Otp.f_username == username)).first()
        if not otp:
            print(f"[!] No OTP found for user '{username}'")
            return

        otp.otp_val = os.urandom(32)
        otp.used = False
        session.add(otp)
        session.commit()
        print(f"[✔] Tampered OTP for user '{username}'")


if __name__ == "__main__":
    import argparse

    from app.shared.db import engine

    def parse_args():
        parser = argparse.ArgumentParser(description="Simulate OTP tampering")
        parser.add_argument("username", type=str, help="Username to modify")
        parser.add_argument("--db", type=str, help="SQLite database path override")
        return parser.parse_args()

    args = parse_args()
    if args.db:
        engine = create_engine(args.db)

    attack_otp(engine, args.username)
