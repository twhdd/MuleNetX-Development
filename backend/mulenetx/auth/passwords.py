"""Argon2id password hashing (SRS §22.1)."""

from __future__ import annotations

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from mulenetx.core.config import Settings

MIN_PASSWORD_LENGTH = 12  # agent default (OQ-15)
MAX_PASSWORD_LENGTH = 256


class Passwords:
    def __init__(self, settings: Settings) -> None:
        self._hasher = PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_kib,
            parallelism=settings.argon2_parallelism,
            type=Type.ID,
        )
        # Used to spend equivalent time when the username is unknown (no user enumeration by timing).
        self._dummy_hash = self._hasher.hash("mulenetx-timing-equalizer")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str | None, password: str) -> bool:
        target = password_hash if password_hash is not None else self._dummy_hash
        try:
            ok = self._hasher.verify(target, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
        return ok and password_hash is not None


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"password must have at least {MIN_PASSWORD_LENGTH} characters"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"password must have at most {MAX_PASSWORD_LENGTH} characters"
    return None
