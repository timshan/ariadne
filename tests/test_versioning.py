import unittest

import lifecycle


class VersioningTests(unittest.TestCase):
    def test_final_semver_rejects_prerelease_and_build_metadata(self):
        self.assertEqual(lifecycle.require_final_semver("1.2.3"), (1, 2, 3))
        for value in ("1.2", "v1.2.3", "1.2.3-rc.1", "1.2.3+build", "01.2.3"):
            with self.subTest(value=value), self.assertRaises(lifecycle.LifecycleError):
                lifecycle.require_final_semver(value)

    def test_authenticated_url_is_redacted(self):
        value = lifecycle.redact("failed https://secret-token@example.com/owner/repo.git")
        self.assertNotIn("secret-token", value)
        self.assertIn("https://example.com/owner/repo.git", value)


if __name__ == "__main__":
    unittest.main()
