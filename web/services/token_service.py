import time
import base64
import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from database.config import get_settings


class TokenService:
    TOKEN_VERSION = 1
    TOKEN_TYPE = "download"
    MAX_LIFETIME_SECONDS = 86400  # 24 hours maximum token lifetime safety cap

    @classmethod
    def generate_download_token(cls, file_id: int, user_id: int, expiry_minutes: Optional[int] = None) -> str:
        """
        Generate a cryptographically signed URL-safe download token with strict schema and expiration.
        """
        if not isinstance(file_id, int) or file_id <= 0:
            raise ValueError(f"Invalid file_id: {file_id}. Must be a positive integer.")
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}. Must be a positive integer.")

        settings = get_settings()
        expiry = expiry_minutes if expiry_minutes is not None else settings.TOKEN_EXPIRY_MINUTES
        now = int(time.time())
        exp = now + (expiry * 60)

        payload = {
            "v": cls.TOKEN_VERSION,
            "typ": cls.TOKEN_TYPE,
            "fid": file_id,
            "uid": user_id,
            "iat": now,
            "exp": exp,
        }

        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

        signature = hmac.new(
            settings.DOWNLOAD_SECRET.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

        return f"{payload_b64}.{sig_b64}"

    @classmethod
    def verify_download_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify the signature, schema, types, and expiration of a download token.
        Returns payload dict if valid, None if expired, invalid, or tampered.
        """
        if not token or not isinstance(token, str) or "." not in token:
            return None

        try:
            settings = get_settings()
            parts = token.split(".")
            if len(parts) != 2:
                return None
            payload_b64, sig_b64 = parts

            # 1. Constant-time signature verification
            expected_sig = hmac.new(
                settings.DOWNLOAD_SECRET.encode("utf-8"),
                payload_b64.encode("utf-8"),
                hashlib.sha256
            ).digest()
            expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

            if not hmac.compare_digest(sig_b64, expected_sig_b64):
                return None

            # 2. Decode payload
            padding = "=" * ((4 - len(payload_b64) % 4) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
            payload = json.loads(payload_bytes.decode("utf-8"))

            if not isinstance(payload, dict):
                return None

            # 3. Validate Token Version and Type
            if payload.get("v") != cls.TOKEN_VERSION:
                return None
            if payload.get("typ") != cls.TOKEN_TYPE:
                return None

            # 4. Validate Positive Integer IDs
            fid = payload.get("fid")
            uid = payload.get("uid")
            if not isinstance(fid, int) or fid <= 0:
                return None
            if not isinstance(uid, int) or uid <= 0:
                return None

            # 5. Validate Timestamps
            iat = payload.get("iat")
            exp = payload.get("exp")
            if not isinstance(iat, int) or not isinstance(exp, int):
                return None

            now = int(time.time())
            if exp <= now:
                return None

            # Enforce max lifetime
            if (exp - iat) > cls.MAX_LIFETIME_SECONDS or exp < iat:
                return None

            return payload
        except Exception:
            return None
