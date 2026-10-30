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

TEMPLATE_PATHS = [
    "landing/templates/index.html",
    "budget_tracker/templates/budget/index.html",
    "calorie_tracker/templates/base.html",
    "fasting_tracker/templates/base.html",
    "workout_tracker/templates/base.html",
    "meal_planner/templates/base.html",
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


class TestViewportMeta:
    """The viewport meta must be fluid and zoomable on every app.

    'user-scalable=no' blocks pinch-zoom; a fixed pixel width breaks on any
    viewport the author did not anticipate (the iPhone Duo's inner display is
    669 or 951 CSS px wide depending on pose).
    """

    def test_no_template_blocks_zoom(self):
        for rel in TEMPLATE_PATHS:
            html = (REPO_ROOT / rel).read_text()
            assert "user-scalable=no" not in html, f"{rel} disables pinch-zoom"

    def test_every_template_declares_viewport_fit_cover(self):
        for rel in TEMPLATE_PATHS:
            html = (REPO_ROOT / rel).read_text()
            assert "viewport-fit=cover" in html, (
                f"{rel} is missing viewport-fit=cover; safe-area insets will "
                "not reach the notch / Duo camera strip"
            )


RAIL_STYLESHEET = "landing/static/shared/rail.css"


class TestRailWiring:
    """The rail stylesheet must exist and reach every app.

    640px is the breakpoint that keeps the iPhone Duo's inner display
    (669 CSS px wide in portrait) in rail mode while the folded outer display
    (382px) and split view (385px) stay in top-bar mode. Chrome on iOS
    renders the Duo at 871px, so the rail must appear below that too.
    """

    def test_every_template_links_the_rail_stylesheet(self):
        for rel in TEMPLATE_PATHS:
            html = (REPO_ROOT / rel).read_text()
            assert "shared/rail.css" in html, f"{rel} does not link rail.css"

    def test_rail_stylesheet_defines_the_breakpoint_contract(self):
        css = (REPO_ROOT / RAIL_STYLESHEET).read_text()
        assert "@media (min-width: 640px)" in css
        assert "--rail-w: 64px" in css
        assert "--rail-item: 44px" in css
