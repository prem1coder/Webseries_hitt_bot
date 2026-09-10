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
        token = TokenService.generate_download_token(file_id=42, user_id=123456789, expiry_minutes=-1)
        payload = TokenService.verify_download_token(token)
        self.assertIsNone(payload)

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

    def test_garbage_token_rejected(self):
        self.assertIsNone(TokenService.verify_download_token("invalid_token_string"))
        self.assertIsNone(TokenService.verify_download_token(""))
        self.assertIsNone(TokenService.verify_download_token(None))
        self.assertIsNone(TokenService.verify_download_token("a.b.c"))

    def test_invalid_types_and_values_rejected(self):
        # Negative / zero IDs should raise error upon creation
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
