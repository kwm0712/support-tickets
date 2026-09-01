from __future__ import annotations

import math
import unittest

from architecture import (
    AuthorizationError,
    PERMISSION_AUDIT_READ,
    PERMISSION_TICKET_WRITE,
    UserContext,
    max_privacy_level,
    require_permission,
    require_privacy_access,
    require_same_tenant,
)
from embedding import DeterministicLocalEmbeddingProvider, cosine_similarity


class V03AuthorizationTests(unittest.TestCase):
    def test_viewer_cannot_write_ticket(self) -> None:
        viewer = UserContext(username="viewer", role="viewer", tenant_id="compelec")
        with self.assertRaises(AuthorizationError):
            require_permission(viewer, PERMISSION_TICKET_WRITE)

    def test_agent_can_write_ticket_but_not_read_audit(self) -> None:
        agent = UserContext(username="support", role="agent", tenant_id="compelec")
        require_permission(agent, PERMISSION_TICKET_WRITE)
        with self.assertRaises(AuthorizationError):
            require_permission(agent, PERMISSION_AUDIT_READ)

    def test_tenant_boundary_is_strict_even_for_admin(self) -> None:
        admin = UserContext(username="admin", role="admin", tenant_id="tenant-a")
        require_same_tenant(admin, "tenant-a")
        with self.assertRaises(AuthorizationError):
            require_same_tenant(admin, "tenant-b")

    def test_privacy_ceiling_follows_role(self) -> None:
        viewer = UserContext(username="viewer", role="viewer", tenant_id="compelec")
        agent = UserContext(username="agent", role="agent", tenant_id="compelec")
        admin = UserContext(username="admin", role="admin", tenant_id="compelec")

        self.assertEqual(max_privacy_level(viewer), "public")
        self.assertEqual(max_privacy_level(agent), "internal")
        self.assertEqual(max_privacy_level(admin), "confidential")

        with self.assertRaises(AuthorizationError):
            require_privacy_access(viewer, "internal")
        require_privacy_access(agent, "internal")
        with self.assertRaises(AuthorizationError):
            require_privacy_access(agent, "confidential")
        require_privacy_access(admin, "confidential")


class V03EmbeddingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = DeterministicLocalEmbeddingProvider()

    def test_embedding_is_deterministic_and_normalized(self) -> None:
        first = self.provider.embed("Datenbank Verbindung prüfen")
        second = self.provider.embed("Datenbank Verbindung prüfen")
        self.assertEqual(first, second)
        self.assertEqual(first.dimensions, 64)
        norm = math.sqrt(sum(value * value for value in first.values))
        self.assertAlmostEqual(norm, 1.0, places=7)

    def test_identical_text_has_full_cosine_similarity(self) -> None:
        left = self.provider.embed("VPN Zertifikat Benutzerkonto")
        right = self.provider.embed("VPN Zertifikat Benutzerkonto")
        self.assertAlmostEqual(cosine_similarity(left, right), 1.0, places=7)

    def test_empty_text_returns_zero_vector(self) -> None:
        vector = self.provider.embed("")
        self.assertEqual(sum(abs(value) for value in vector.values), 0.0)


if __name__ == "__main__":
    unittest.main()
