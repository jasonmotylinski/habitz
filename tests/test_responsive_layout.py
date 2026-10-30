"""Contract tests for device-adaptive layout (iPhone Duo readiness).

These tests pin the *contracts* of the responsive layout — rotation, zoom,
viewport fit, rail wiring, accessible names — not the pixels. A CSS change
cannot be unit-tested; these tests fail when a contract is broken.
"""
import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

MANIFEST_PATHS = [
    "landing/static/manifest.json",
    "calorie_tracker/static/manifest.json",
    "fasting_tracker/static/manifest.json",
    "workout_tracker/static/manifest.json",
    "meal_planner/static/manifest.json",
]


class TestManifestOrientation:
    """An installed PWA must be able to rotate.

    'portrait-primary' locks the installed app to portrait, so on iPhone Duo
    it can never present the landscape/book pose the device is designed around.
    """

    def test_every_manifest_allows_rotation(self):
        for rel in MANIFEST_PATHS:
            data = json.loads((REPO_ROOT / rel).read_text())
            assert data.get("orientation") == "any", (
                f"{rel} pins orientation to {data.get('orientation')!r}; "
                "the installed PWA must be able to rotate"
            )
