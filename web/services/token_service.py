import time
import base64
import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from database.config import get_settings


class TokenService:
    @staticmethod
    def generate_download_token(file_id: int, user_id: int, expiry_minutes: Optional[int] = None) -> str:
        """Generate a cryptographically signed URL-safe download token with expiration."""
        settings = get_settings()
        expiry = expiry_minutes or settings.TOKEN_EXPIRY_MINUTES
        now = int(time.time())
        exp = now + (expiry * 60)

        payload = {
            "fid": file_id,
            "uid": user_id,
            "iat": now,
            "exp": exp
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

    @staticmethod
    def verify_download_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify the signature and expiration of a download token.
        Returns payload dict if valid, None if expired, invalid, or tampered.
        """
        if not token or "." not in token:
            return None

        try:
            settings = get_settings()
            payload_b64, sig_b64 = token.split(".", 1)

            # Check signature
            expected_sig = hmac.new(
                settings.DOWNLOAD_SECRET.encode("utf-8"),
                payload_b64.encode("utf-8"),
                hashlib.sha256
            ).digest()
            expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

            if not hmac.compare_digest(sig_b64, expected_sig_b64):
                return None

            # Add back base64 padding
            padding = "=" * ((4 - len(payload_b64) % 4) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
            payload = json.loads(payload_bytes.decode("utf-8"))

            # Check expiration
            now = int(time.time())
            if payload.get("exp", 0) < now:
                return None

            return payload
        except Exception:
            return None
