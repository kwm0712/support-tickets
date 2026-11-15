from __future__ import annotations
import base64, json, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from license_verifier import LicenseValidationError, verify_license_file

class SignedLicenseTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.public = base64.b64encode(self.private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        self.now = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
        self.payload = {"product":"compelec-one-business","tenant_id":"compelec","issued_at":"2026-11-01T00:00:00Z","expires_at":"2027-11-01T00:00:00Z","features":["support","knowledge"]}
    def write(self, payload=None, signed=None):
        data = self.payload if payload is None else payload
        original = data if signed is None else signed
        raw = json.dumps(original, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        envelope = {"payload":data,"signature":base64.b64encode(self.private.sign(raw)).decode()}
        f = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
        json.dump(envelope, f); f.close(); self.addCleanup(Path(f.name).unlink, missing_ok=True)
        return f.name
    def test_valid_license(self):
        result=verify_license_file(self.write(),self.public,expected_tenant="compelec",now=self.now)
        self.assertEqual(result.features,("support","knowledge"))
    def test_tampered_payload_rejected(self):
        changed=dict(self.payload,features=["admin"])
        with self.assertRaisesRegex(LicenseValidationError,"(?i)signatur"): verify_license_file(self.write(changed,self.payload),self.public,expected_tenant="compelec",now=self.now)
    def test_wrong_tenant_rejected(self):
        with self.assertRaisesRegex(LicenseValidationError,"anderen"): verify_license_file(self.write(),self.public,expected_tenant="other",now=self.now)
    def test_expired_license_rejected(self):
        expired=dict(self.payload,expires_at="2026-11-10T00:00:00Z")
        with self.assertRaisesRegex(LicenseValidationError,"abgelaufen"): verify_license_file(self.write(expired),self.public,expected_tenant="compelec",now=self.now)
    def test_wrong_product_rejected(self):
        wrong=dict(self.payload,product="other")
        with self.assertRaisesRegex(LicenseValidationError,"nicht für"): verify_license_file(self.write(wrong),self.public,expected_tenant="compelec",now=self.now)
    def test_missing_public_key_rejected(self):
        with self.assertRaisesRegex(LicenseValidationError,"(?i)prüfschlüssel"): verify_license_file(self.write(),"",expected_tenant="compelec",now=self.now)

if __name__ == "__main__": unittest.main()
