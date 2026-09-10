import unittest
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web.services.token_service import TokenService


class TestTokenService(unittest.TestCase):
    def test_valid_token_generation_and_verification(self):
        token = TokenService.generate_download_token(file_id=42, user_id=123456789, expiry_minutes=15)
        payload = TokenService.verify_download_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["fid"], 42)
        self.assertEqual(payload["uid"], 123456789)
        self.assertTrue(payload["exp"] > time.time())

    def test_expired_token_rejected(self):
        # Generate token with negative expiry
        token = TokenService.generate_download_token(file_id=42, user_id=123456789, expiry_minutes=-1)
        payload = TokenService.verify_download_token(token)
        self.assertIsNone(payload)

    def test_tampered_token_rejected(self):
        token = TokenService.generate_download_token(file_id=42, user_id=123456789, expiry_minutes=15)
        # Tamper payload
        parts = token.split(".")
        tampered_token = f"extra_{parts[0]}.{parts[1]}"
        self.assertIsNone(TokenService.verify_download_token(tampered_token))

    def test_garbage_token_rejected(self):
        self.assertIsNone(TokenService.verify_download_token("invalid_token_string"))
        self.assertIsNone(TokenService.verify_download_token(""))


if __name__ == "__main__":
    unittest.main()
