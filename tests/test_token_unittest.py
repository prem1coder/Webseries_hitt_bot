import unittest
import time
import sys
import os
import base64
import json
import hmac
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web.services.token_service import TokenService
from database.config import get_settings


class TestTokenService(unittest.TestCase):
    def test_valid_token_generation_and_verification(self):
        token = TokenService.generate_download_token(file_id=42, user_id=123456789, expiry_minutes=15)
        payload = TokenService.verify_download_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["v"], 1)
        self.assertEqual(payload["typ"], "download")
        self.assertEqual(payload["fid"], 42)
        self.assertEqual(payload["uid"], 123456789)
        self.assertIsInstance(payload["iat"], int)
        self.assertTrue(payload["exp"] > time.time())

    def test_expired_token_rejected(self):
        settings = get_settings()
        now = int(time.time())
        fake_payload = {
            "v": 1,
            "typ": "download",
            "fid": 42,
            "uid": 123456789,
            "iat": now - 3600,
            "exp": now - 60  # expired 60s ago
        }
        raw_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode("utf-8")).decode("utf-8").rstrip("=")
        sig = hmac.new(settings.DOWNLOAD_SECRET.encode("utf-8"), raw_b64.encode("utf-8"), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
        token = f"{raw_b64}.{sig_b64}"

        self.assertIsNone(TokenService.verify_download_token(token))

    def test_future_iat_rejected(self):
        """Reject tokens claiming to be issued far in the future (>60s clock skew)."""
        settings = get_settings()
        now = int(time.time())
        fake_payload = {
            "v": 1,
            "typ": "download",
            "fid": 42,
            "uid": 123456789,
            "iat": now + 3600,  # 1 hour in future
            "exp": now + 7200
        }
        raw_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode("utf-8")).decode("utf-8").rstrip("=")
        sig = hmac.new(settings.DOWNLOAD_SECRET.encode("utf-8"), raw_b64.encode("utf-8"), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
        token = f"{raw_b64}.{sig_b64}"

        self.assertIsNone(TokenService.verify_download_token(token))

    def test_too_long_lifetime_rejected(self):
        """Reject tokens exceeding maximum lifetime safety cap."""
        settings = get_settings()
        now = int(time.time())
        fake_payload = {
            "v": 1,
            "typ": "download",
            "fid": 42,
            "uid": 123456789,
            "iat": now,
            "exp": now + 100000  # exceeds MAX_LIFETIME_SECONDS (86400)
        }
        raw_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode("utf-8")).decode("utf-8").rstrip("=")
        sig = hmac.new(settings.DOWNLOAD_SECRET.encode("utf-8"), raw_b64.encode("utf-8"), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
        token = f"{raw_b64}.{sig_b64}"

        self.assertIsNone(TokenService.verify_download_token(token))

    def test_missing_or_extra_keys_rejected(self):
        """Reject tokens with missing or extraneous keys in payload."""
        settings = get_settings()
        now = int(time.time())

        # Extra key
        extra_payload = {
            "v": 1, "typ": "download", "fid": 42, "uid": 123456789,
            "iat": now, "exp": now + 600, "is_admin": True
        }
        raw_b64 = base64.urlsafe_b64encode(json.dumps(extra_payload).encode("utf-8")).decode("utf-8").rstrip("=")
        sig = hmac.new(settings.DOWNLOAD_SECRET.encode("utf-8"), raw_b64.encode("utf-8"), hashlib.sha256).digest()
        self.assertIsNone(TokenService.verify_download_token(f"{raw_b64}.{base64.urlsafe_b64encode(sig).decode().rstrip('=')}"))

        # Missing key (missing uid)
        missing_payload = {
            "v": 1, "typ": "download", "fid": 42,
            "iat": now, "exp": now + 600
        }
        raw_b64 = base64.urlsafe_b64encode(json.dumps(missing_payload).encode("utf-8")).decode("utf-8").rstrip("=")
        sig = hmac.new(settings.DOWNLOAD_SECRET.encode("utf-8"), raw_b64.encode("utf-8"), hashlib.sha256).digest()
        self.assertIsNone(TokenService.verify_download_token(f"{raw_b64}.{base64.urlsafe_b64encode(sig).decode().rstrip('=')}"))

    def test_boolean_id_rejected(self):
        """Reject boolean IDs (which are subclasses of int in Python)."""
        settings = get_settings()
        now = int(time.time())
        fake_payload = {
            "v": 1, "typ": "download", "fid": True, "uid": 123456789,
            "iat": now, "exp": now + 600
        }
        raw_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode("utf-8")).decode("utf-8").rstrip("=")
        sig = hmac.new(settings.DOWNLOAD_SECRET.encode("utf-8"), raw_b64.encode("utf-8"), hashlib.sha256).digest()
        self.assertIsNone(TokenService.verify_download_token(f"{raw_b64}.{base64.urlsafe_b64encode(sig).decode().rstrip('=')}"))

    def test_tampered_token_rejected(self):
        token = TokenService.generate_download_token(file_id=42, user_id=123456789, expiry_minutes=15)
        parts = token.split(".")
        tampered_token = f"extra_{parts[0]}.{parts[1]}"
        self.assertIsNone(TokenService.verify_download_token(tampered_token))

    def test_tampered_signature_rejected(self):
        token = TokenService.generate_download_token(file_id=42, user_id=123456789, expiry_minutes=15)
        parts = token.split(".")
        tampered_sig = parts[1][:-2] + ("aa" if not parts[1].endswith("aa") else "bb")
        self.assertIsNone(TokenService.verify_download_token(f"{parts[0]}.{tampered_sig}"))

    def test_garbage_and_invalid_base64_rejected(self):
        self.assertIsNone(TokenService.verify_download_token("invalid_token_string"))
        self.assertIsNone(TokenService.verify_download_token(""))
        self.assertIsNone(TokenService.verify_download_token(None))
        self.assertIsNone(TokenService.verify_download_token("a.b.c"))
        self.assertIsNone(TokenService.verify_download_token("!!!not_base64!!!.valid_sig"))
        self.assertIsNone(TokenService.verify_download_token("."))

    def test_ttl_bounds_enforced_at_generation(self):
        """Enforce configured TTL bounds at generation time (1 to 1440 minutes)."""
        with self.assertRaises(ValueError):
            TokenService.generate_download_token(file_id=1, user_id=1, expiry_minutes=0)
        with self.assertRaises(ValueError):
            TokenService.generate_download_token(file_id=1, user_id=1, expiry_minutes=-10)
        with self.assertRaises(ValueError):
            TokenService.generate_download_token(file_id=1, user_id=1, expiry_minutes=2000)

    def test_invalid_types_and_values_rejected(self):
        with self.assertRaises(ValueError):
            TokenService.generate_download_token(file_id=-1, user_id=100)
        with self.assertRaises(ValueError):
            TokenService.generate_download_token(file_id=10, user_id=0)
    def test_crafted_token_wrong_secret_rejected(self):
        now = int(time.time())
        fake_payload = {
            "v": 1,
            "typ": "download",
            "fid": 10,
            "uid": 20,
            "iat": now,
            "exp": now + 600
        }
        raw_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode("utf-8")).decode("utf-8").rstrip("=")
        wrong_sig = hmac.new(b"wrong_secret_key", raw_b64.encode("utf-8"), hashlib.sha256).digest()
        wrong_sig_b64 = base64.urlsafe_b64encode(wrong_sig).decode("utf-8").rstrip("=")
        crafted_token = f"{raw_b64}.{wrong_sig_b64}"

        self.assertIsNone(TokenService.verify_download_token(crafted_token))

    def test_crafted_token_wrong_type_rejected(self):
        settings = get_settings()
        now = int(time.time())
        fake_payload = {
            "v": 1,
            "typ": "admin_access",  # wrong type
            "fid": 10,
            "uid": 20,
            "iat": now,
            "exp": now + 600
        }
        raw_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode("utf-8")).decode("utf-8").rstrip("=")
        sig = hmac.new(settings.DOWNLOAD_SECRET.encode("utf-8"), raw_b64.encode("utf-8"), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
        crafted_token = f"{raw_b64}.{sig_b64}"

        self.assertIsNone(TokenService.verify_download_token(crafted_token))


if __name__ == "__main__":
    unittest.main()
