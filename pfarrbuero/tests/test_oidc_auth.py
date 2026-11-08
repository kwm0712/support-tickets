import base64
import hashlib
import unittest

from oidc_auth import create_pkce_pair, verify_oauth_state


class PkceTests(unittest.TestCase):
    def test_pkce_pair_uses_s256_and_valid_verifier_length(self):
        verifier, challenge = create_pkce_pair()
        self.assertGreaterEqual(len(verifier), 43)
        self.assertLessEqual(len(verifier), 128)
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        self.assertEqual(challenge, expected)
        self.assertNotEqual(challenge, verifier)

    def test_state_accepts_exact_match(self):
        verify_oauth_state("state-value", "state-value")

    def test_state_rejects_mismatch(self):
        with self.assertRaises(RuntimeError):
            verify_oauth_state("attacker-state", "expected-state")

    def test_state_rejects_missing_value(self):
        with self.assertRaises(RuntimeError):
            verify_oauth_state("", "expected-state")


if __name__ == "__main__":
    unittest.main()
