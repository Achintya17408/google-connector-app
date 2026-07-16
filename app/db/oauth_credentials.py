import base64
import hashlib
import json

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

from app.config.settings import get_settings
from app.db.google_clients import SCOPES


def _fernet() -> Fernet:
    secret = get_settings().jwt_secret_key.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


async def save_google_credentials(pool, email: str, credentials: Credentials):
    payload = _fernet().encrypt(credentials.to_json().encode()).decode()
    scopes = list(credentials.scopes or SCOPES)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO google_oauth_credentials
               (user_id,email,encrypted_credentials,granted_scopes,updated_at)
               VALUES($1,$1,$2,$3,now())
               ON CONFLICT(user_id) DO UPDATE SET
                 email=EXCLUDED.email,
                 encrypted_credentials=EXCLUDED.encrypted_credentials,
                 granted_scopes=EXCLUDED.granted_scopes,
                 updated_at=now()""",
            email,
            payload,
            scopes,
        )


async def load_google_credentials(pool, user_id: str) -> Credentials | None:
    async with pool.acquire() as conn:
        payload = await conn.fetchval(
            "SELECT encrypted_credentials FROM google_oauth_credentials WHERE user_id=$1",
            user_id,
        )
    if not payload:
        return None
    info = json.loads(_fernet().decrypt(payload.encode()).decode())
    credentials = Credentials.from_authorized_user_info(info, SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        await save_google_credentials(pool, user_id, credentials)
    return credentials


async def delete_google_credentials(pool, user_id: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM google_oauth_credentials WHERE user_id=$1", user_id
        )
