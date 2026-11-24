"""Credentials and tokens for member auth (guide §6.2, P-04).

- Passwords: Argon2id (argon2-cffi defaults). Never stored or logged in plain text.
- Access token: HS256 JWT, 15 minutes, carries the user id and `ver` (users.token_version).
- Refresh token / verification token: 256-bit random values; only SHA-256 hashes are stored.
- Verification codes: 6 digits, stored as an HMAC keyed by AUTH_JWT_SECRET so a leaked table
  cannot be brute-forced offline (a million codes would be trivial with a plain hash).
"""

import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import settings

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=14)
JWT_ALGORITHM = "HS256"

# P-04 (user decision 2026-11-01). The signup hints say exactly this.
NICKNAME_MIN, NICKNAME_MAX = 2, 12
PASSWORD_MIN, PASSWORD_MAX = 8, 64
NICKNAME_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+")
EMAIL_MAX = 254
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

NICKNAME_RULE = "닉네임은 2~12자 완성형 한글·영문·숫자로 입력해 주세요."
NICKNAME_BLOCKED = "사용할 수 없는 닉네임입니다."
# A nickname may not contain these (user decision 2026-11-24): words that pass for the
# operator, and direct profanity. Compared in lower case with digits removed, so "Admin1" or
# "씨8발" are caught too. Accounts made before the rule keep their nickname. The signup
# screen uses the same list (frontend `features/auth/rules.ts`, kept equal by a test).
# fmt: off
BLOCKED_NICKNAME_WORDS = (
    # operator impersonation
    "관리자", "운영자", "운영진", "운영팀", "킥탭", "고객센터", "공식",
    "kicktab", "admin", "moderator", "official", "staff",
    # direct profanity and its common spellings
    "씨발", "시발", "씨바", "씨빨", "시빨", "씹", "병신", "븅신", "빙신", "개새", "개색",
    "좆", "존나", "지랄", "썅", "미친놈", "미친년", "엠창", "느금", "섹스",
    "fuck", "shit", "bitch", "sibal", "ssibal", "tlqkf", "qudtls",
)
# fmt: on
PASSWORD_RULE = "비밀번호는 8~64자, 영문과 숫자를 각각 1자 이상 포함해 주세요."
EMAIL_RULE = "이메일 주소 형식을 확인해 주세요."
CONFIRM_RULE = "비밀번호 확인이 일치하지 않습니다."

_hasher = PasswordHasher()


class AuthNotConfigured(Exception):
    """AUTH_JWT_SECRET is empty: no token may be signed or checked."""


def normalize_email(value: str) -> str:
    return value.strip().lower()


def email_error(value: str) -> str | None:
    email = normalize_email(value)
    if not email or len(email) > EMAIL_MAX or not EMAIL_PATTERN.fullmatch(email):
        return EMAIL_RULE
    return None


def nickname_error(value: str) -> str | None:
    # fullmatch: `$` alone also matches before a trailing line break.
    if not NICKNAME_MIN <= len(value) <= NICKNAME_MAX or not NICKNAME_PATTERN.fullmatch(value):
        return NICKNAME_RULE
    if nickname_blocked(value):
        return NICKNAME_BLOCKED
    return None


def nickname_blocked(value: str) -> bool:
    plain = re.sub(r"[0-9]", "", value).lower()
    return any(word in plain for word in BLOCKED_NICKNAME_WORDS)


def password_error(value: str) -> str | None:
    if (
        not PASSWORD_MIN <= len(value) <= PASSWORD_MAX
        or not re.search(r"[A-Za-z]", value)
        or not re.search(r"[0-9]", value)
    ):
        return PASSWORD_RULE
    return None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# A real hash to compare against when the account does not exist, so a login for an
# unknown email takes as long as one with a wrong password.
_DUMMY_HASH = _hasher.hash("kicktab-no-account-0")


def verify_password_or_dummy(password_hash: str | None, password: str) -> bool:
    if password_hash is None:
        verify_password(_DUMMY_HASH, password)
        return False
    return verify_password(password_hash, password)


def _secret() -> str:
    secret = settings.auth_jwt_secret.get_secret_value()
    if not secret:
        raise AuthNotConfigured
    return secret


def new_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def code_hash(email: str, purpose: str, code: str) -> str:
    message = f"{purpose}:{email}:{code}".encode()
    return hmac.new(_secret().encode(), message, hashlib.sha256).hexdigest()


def codes_match(stored: str, email: str, purpose: str, code: str) -> bool:
    return hmac.compare_digest(stored, code_hash(email, purpose, code))


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    version: int


class AccessTokenExpired(Exception):
    pass


class AccessTokenInvalid(Exception):
    pass


def encode_access_token(user_id: uuid.UUID, version: int, now: datetime | None = None) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "ver": version,
        "iat": int(issued.timestamp()),
        "exp": int((issued + ACCESS_TOKEN_TTL).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> AccessClaims:
    try:
        payload = jwt.decode(
            token, _secret(), algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]}
        )
    except jwt.ExpiredSignatureError:
        raise AccessTokenExpired from None
    except jwt.PyJWTError:
        raise AccessTokenInvalid from None
    if payload.get("typ") != "access":
        raise AccessTokenInvalid
    try:
        return AccessClaims(user_id=uuid.UUID(payload["sub"]), version=int(payload.get("ver", 0)))
    except (ValueError, TypeError):
        raise AccessTokenInvalid from None
