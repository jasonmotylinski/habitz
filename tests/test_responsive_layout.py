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


def stylesheet_links(html: str) -> list[str]:
    """The stylesheet <link> tags of the document head, in load order."""
    import re

    link_re = re.compile(r"<link[^>]*rel=[\"']stylesheet[\"'][^>]*>")
    head = html.split("</head>", 1)[0]
    return [m.group(0) for m in link_re.finditer(head)]


# Every template that carries a header and therefore must load the rail.
RAIL_LINKED_TEMPLATE_PATHS = TEMPLATE_PATHS + [
    "landing/templates/history.html",
    "landing/templates/habit_form.html",
]


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
            links = stylesheet_links(html)
            assert any("shared/rail.css" in tag for tag in links), (
                f"{rel} does not link rail.css as a stylesheet"
            )

    def test_rail_stylesheet_is_loaded_after_the_module_stylesheets(self):
        """Load order is the contract: the rail must win on equal specificity.

        rail.css and the module stylesheets often target the same selectors
        (e.g. `.app-header`); without rail.css coming last, the module rules
        would win and the rail would never take shape.
        """
        for rel in RAIL_LINKED_TEMPLATE_PATHS:
            html = (REPO_ROOT / rel).read_text()
            links = stylesheet_links(html)
            rail_positions = [i for i, tag in enumerate(links) if "shared/rail.css" in tag]
            assert rail_positions, f"{rel} does not link rail.css"
            rail_at = rail_positions[0]
            others = [
                (i, tag)
                for i, tag in enumerate(links)
                if "shared/rail.css" not in tag
            ]
            for i, link in others:
                assert i < rail_at, (
                    f"{rel}: {link.strip()} is loaded after rail.css — the rail "
                    "rules would lose on equal specificity"
                )

    def test_rail_stylesheet_defines_the_breakpoint_contract(self):
        css = (REPO_ROOT / RAIL_STYLESHEET).read_text()
        assert "@media (min-width: 640px)" in css
        assert "--rail-w: 64px" in css
        assert "--rail-item: 44px" in css


CONTROL_CLASSES = ("nav-link", "logout-link", "btn-new", "app-switcher-btn", "nav-brand")


def assert_controls_have_aria_labels(html: str, rel: str) -> None:
    """Every nav/control element must carry a non-empty accessible name.

    In rail mode the visible text is display:none (`.nav-label`, `.nav-title`),
    so aria-label is the only name the control has.
    """
    import re

    tag_re = re.compile(r"<(a|button)\b[^>]*>")
    class_re = re.compile(r"class=(?:\"([^\"]*)\"|'([^']*)')")
    label_re = re.compile(r"aria-label=(?:\"([^\"]*)\"|'([^']*)')")

    controls = []
    for match in tag_re.finditer(html):
        tag = match.group(0)
        class_match = class_re.search(tag)
        if not class_match:
            continue
        classes = (class_match.group(1) or class_match.group(2) or "").split()
        if any(name in classes for name in CONTROL_CLASSES):
            controls.append(tag)

    assert controls, (
        f"{rel}: no control matched {CONTROL_CLASSES} — the selector is stale, "
        "so this check would pass without testing anything"
    )

    for tag in controls:
        label_match = label_re.search(tag)
        label = (label_match.group(1) or label_match.group(2) or "") if label_match else ""
        assert label.strip(), (
            f"{rel}: control without a non-empty accessible name -> {tag[:140]}"
        )


class TestLandingRail:
    def test_landing_header_controls_have_accessible_names(self):
        rel = "landing/templates/index.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)


class TestLandingSecondaryRail:
    def test_history_header_controls_have_accessible_names(self):
        rel = "landing/templates/history.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)

    def test_habit_form_header_controls_have_accessible_names(self):
        rel = "landing/templates/habit_form.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)

    def test_secondary_landing_templates_link_the_rail_stylesheet(self):
        for rel in ("landing/templates/history.html", "landing/templates/habit_form.html"):
            html = (REPO_ROOT / rel).read_text()
            links = stylesheet_links(html)
            assert any("shared/rail.css" in tag for tag in links), (
                f"{rel} does not link the shared rail stylesheet"
            )


class TestBudgetRail:
    def test_budget_header_controls_have_accessible_names(self):
        rel = "budget_tracker/templates/budget/index.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)


class TestNavbarFamilyRails:
    def test_calorie_and_fasting_nav_links_have_accessible_names(self):
        for rel in ("calorie_tracker/templates/base.html",
                    "fasting_tracker/templates/base.html"):
            assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)


class TestWorkoutRail:
    def test_workout_nav_links_have_accessible_names(self):
        rel = "workout_tracker/templates/base.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)


class TestMealRail:
    def test_meal_nav_links_have_accessible_names(self):
        rel = "meal_planner/templates/base.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)

    def test_meal_toast_clears_the_rail(self):
        """The toast is fixed to the bottom-right — over the rail without an offset."""
        css = strip_css_comments((REPO_ROOT / "meal_planner/static/css/components.css").read_text())
        bodies = media_block_bodies(css, "min-width: 640px")
        assert any(
            ".toast" in body and "--rail-w" in body and "right:" in body for body in bodies
        ), "meal_planner: .toast needs a rail-aware right offset at >=640px"


# module -> (stylesheet that declares the colour tokens,
#            stylesheet that carries the >=640px rail block)
# The meal module keeps its tokens in base.css and its navbar rules in
# components.css; every other module keeps both in one file.
MODULE_STYLESHEETS = {
    "landing": ("landing/static/css/habits.css", "landing/static/css/habits.css"),
    "budget": ("budget_tracker/static/css/budget.css", "budget_tracker/static/css/budget.css"),
    "calorie": ("calorie_tracker/static/css/base.css", "calorie_tracker/static/css/base.css"),
    "fasting": ("fasting_tracker/static/css/base.css", "fasting_tracker/static/css/base.css"),
    "workout": ("workout_tracker/static/css/style.css", "workout_tracker/static/css/style.css"),
    "meal": ("meal_planner/static/css/base.css", "meal_planner/static/css/components.css"),
}


def strip_css_comments(css: str) -> str:
    import re

    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def root_block_bodies(css: str) -> list[str]:
    """The body of every `:root { … }` block, comments stripped."""
    import re

    css = strip_css_comments(css)
    return re.findall(r":root\s*\{([^}]*)\}", css)


def media_block_body(css: str, condition: str) -> str | None:
    """The body of the first `@media (condition) { … }` block, or None.

    Brace-matched so a nested rule cannot end the block early.
    """
    at = css.find(f"@media ({condition})")
    if at == -1:
        return None
    open_brace = css.find("{", at)
    depth = 0
    for i in range(open_brace, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[open_brace + 1 : i]
    return None


def media_block_bodies(css: str, condition: str) -> list[str]:
    """The body of every `@media (condition) { … }` block, comments stripped.

    A module can legitimately own several blocks with the same condition —
    calorie and fasting each have a content-width block and their rail block.
    """
    css = strip_css_comments(css)
    bodies = []
    at = 0
    while (at := css.find(f"@media ({condition})", at)) != -1:
        body = media_block_body(css[at:], condition)
        if body is None:
            break
        bodies.append(body)
        at += 1
    return bodies


class TestRailCrossModuleContract:
    """Every module must honour the same rail contract.

    The per-module tests above pin one module each; nothing else asserts the
    contract they all have to follow: declare your own `--rail-bg` /
    `--rail-border` in your own `:root` (Module Color Sovereignty), and ship a
    non-empty `@media (min-width: 640px)` rail block. The shared stylesheet
    owns geometry only.
    """

    def test_every_module_declares_rail_colour_tokens_in_root(self):
        for module, (token_sheet, _) in MODULE_STYLESHEETS.items():
            css = (REPO_ROOT / token_sheet).read_text()
            bodies = root_block_bodies(css)
            assert any("--rail-bg:" in body and "--rail-border:" in body for body in bodies), (
                f"{module}: {token_sheet} must declare --rail-bg: and --rail-border: "
                "inside a :root block (Module Color Sovereignty)"
            )

    def test_every_module_ships_a_non_empty_rail_media_block(self):
        for module, (_, rail_sheet) in MODULE_STYLESHEETS.items():
            css = (REPO_ROOT / rail_sheet).read_text()
            bodies = media_block_bodies(css, "min-width: 640px")
            assert bodies, (
                f"{module}: {rail_sheet} has no @media (min-width: 640px) block — "
                "the module would stay in top-bar mode on the iPhone Duo"
            )
            # The rail block, not merely some 640px block: a module can have
            # an older content-width block first, which would pass on its own.
            rail_selectors = (".app-header", ".navbar")
            assert any(
                body.strip() and any(sel in body for sel in rail_selectors) for body in bodies
            ), (
                f"{module}: no non-empty @media (min-width: 640px) block contains "
                f"{' or '.join(rail_selectors)} — {rail_sheet} has no rail block"
            )

    def test_shared_rail_stylesheet_declares_geometry_only(self):
        css = strip_css_comments((REPO_ROOT / RAIL_STYLESHEET).read_text())
        assert "--rail-w: 64px" in css
        assert "--rail-item: 44px" in css
        assert "--rail-bg:" not in css, (
            f"{RAIL_STYLESHEET} declares --rail-bg; colour belongs to each module's "
            ":root (Module Color Sovereignty)"
        )
        assert "--rail-border:" not in css, (
            f"{RAIL_STYLESHEET} declares --rail-border; colour belongs to each module's "
            ":root (Module Color Sovereignty)"
        )

    def test_shared_rail_stylesheet_centres_content_around_the_rail(self):
        """Content keeps an equal gutter on both sides of the rail.

        The rail takes --rail-w off the right edge only; offsetting the right
        side alone leaves `margin: 0 auto` columns visibly off the middle of
        the screen (reported on the landing dashboard on a real iPhone Duo).
        """
        css = strip_css_comments((REPO_ROOT / RAIL_STYLESHEET).read_text())
        body = media_block_body(css, "min-width: 640px")
        assert body is not None
        assert "padding-left: var(--rail-w)" in body, (
            f"{RAIL_STYLESHEET}: rail mode must offset the left edge by --rail-w too, "
            "so centred columns stay centred on the screen"
        )
        assert "padding-right: calc(var(--rail-w) + var(--rail-inset-right))" in body
