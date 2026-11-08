# iPhone Duo Navigation Rail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Habitz lay out correctly on the iPhone Duo (and every wide viewport) by moving navigation from a horizontal top bar into a vertical right-side rail, and by unblocking rotation/zoom that currently prevent the app from adapting to new device geometry.

**Architecture:** Habitz is a Flask PWA (server-rendered Jinja2 + custom CSS per module), not a native iOS app — Apple's native bar-relocation does not apply to us, so we build the side rail ourselves in CSS. The existing header markup is *re-laid out* rather than duplicated: the same `<header class="app-header">` / `<nav class="navbar">` element becomes the rail at `min-width: 640px` by switching to `position: fixed` + a vertical flex column, and `display: contents` on the intermediate wrappers lets their children become rail items without duplicating any nav link. A new shared stylesheet `landing/static/shared/rail.css` owns the generic rail geometry; each module keeps ownership of its own colours (tokens declared in that module's `:root`).

**Tech Stack:** Flask + Jinja2, vanilla CSS (no framework, no build step), SQLite/SQLAlchemy untouched, pytest for the layout contract tests.

**Spec:** `DESIGN.md` + `PRODUCT.md` (repo design system, both currently untracked) and the "Research basis" + "Approved design decisions" sections below. No separate written spec exists — the approved design is recorded here.

---

## Research basis (Apple's published guidance)

Sources consulted, 2026-10-30. Nothing here is inferred from rumour; each item is from Apple or WebKit.

**Apple HIG — "Designing for iPhone Duo"** (new page, 2026-09-09, `developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo`)

- iPhone Duo: 5.4″ outer display (1398×2034, 460 ppi), 7.6″ inner folding display (1878×2670, 430 ppi), ships 2026-10-23, iOS 27.
- "People interact with the outer display when the device is closed, and the system places toolbars and tab bars on the side to maximize the vertical space for content. The controls remain on the side when the device opens in landscape to ensure a consistent experience as people move between displays."
- "Build your layouts with layout margins and safe area insets, and steer clear of fixed widths or anything tied to a specific display."
- "Account for asymmetry in your layouts… Use safe areas to make sure controls don't cover your content, including controls on the opposite edge."
- When space is limited, compress **one** bar only: navigation-focused → keep the tab bar and overflow the toolbar; task-oriented → minimize the tab bar and keep the toolbar actions.

**Apple HIG — Layout** (`.../layout`)

- "On iPhone Duo, toolbars, tab bars, and navigation controls that are typically at the top and bottom of the display move to the side… The exception is the inner display in portrait, which has enough vertical space to keep standard horizontal bars."
- "Don't change your app's functionality based on the space it occupies… keep the layout recognizable and familiar to the platform even when resizing."
- "Don't treat 'regular width' as 'iPad'."

**Apple Developer — "Prepare for iPhone Duo"** (`developer.apple.com/iphone-duo/prepare/`)

- "Hardcoded screen sizes, fixed orientations, and device assumptions can break layouts."
- SDK ladder: iOS 26 SDK → letterboxed on the inner display; iOS 27 SDK → fills most of the inner display; **iOS 27.1 SDK → extends edge to edge on both displays, with toolbar buttons laid out vertically under the status bar.**
- "Stop assuming idiom or size class identifies the device"; size from the view/window, re-read on every change; never store a `UIScreen`.

**WebKit — "WebKit Features for Safari 27.1"** (2026-10-23, `webkit.org/blog/18486/webkit-features-for-safari-27-1/`)

- Safari 27.1 viewport widths on the Duo (CSS px):

  | Pose | Width | Small viewport height | Large viewport height |
  |---|---|---|---|
  | Outer display, portrait | 382 | 580 | 618 |
  | Outer display, landscape | 594 | 368 | 406 |
  | Inner display, portrait (one tab) | 669 | 867 | 902 |
  | Inner display, landscape (one tab) | 951 | 585 | 620 |
  | Inner display, two windows side by side (each) | 385 | 571 | 609 |

- The outer display reserves an **84pt vertical strip on the right** for the camera, clock, signal and Safari buttons. `screen.width` reports 466 but `window.innerWidth` is 382 — **web content never draws into that strip**; Safari extends the page background colour into it and samples the colour of fixed/sticky elements at the right edge.
- `screen.width` / `screen.height` read 466×678 in *every* pose → never size layout from `screen`.
- "Unfolding shows the wide layout first… the page draws at 951 wide for 0.9 seconds. Then it settles at 669. Every change fires a resize event with the right size. Nothing reloads. **A layout that listens for resize ends up right. A script that measures once at load ends up wrong.**"
- The crease sits at x ≈ 475.5 in the 951px inner viewport — centred hero text, single CTA buttons and centred form fields land directly on it. There is no Safari media query for the hinge yet.
- Chrome on iOS renders the Duo at **871px**, not 951px.
- WebKit's guidance for site authors: do not sniff the device; use flexible layouts / media queries on width; test in the iPhone Duo simulator (Xcode 27.1+, Device Hub).
- `device-posture` (Device Posture API) and `horizontal-viewport-segments` (Viewport Segments API) exist in Safari 27.1 **only behind Settings → Apps → Safari → Advanced → Feature Flags** (off by default). Unknown media queries are safely ignored, so they may be used as a forward-compatible enhancement but must never be load-bearing.

**Why this plan does not simply copy iOS's behaviour:** iOS moves *its own* chrome to the side of the outer display. On the web, that strip belongs to Safari. A web app has to earn the side rail itself, with CSS, at a breakpoint chosen from real viewport widths — which is exactly what the table above gives us.

## Approved design decisions

Agreed with the user before this plan was written:

1. **Form — icon rail.** A narrow vertical strip pinned to the **right edge** (user ruling, 2026-11-08 — the first build pinned it left): app switcher at the top, module nav icons stacked vertically, user/logout pinned to the bottom. The horizontal top bar disappears at wide widths.
2. **Scope — shell only.** Rail + top-bar fallback across all six apps. Content layout is untouched: each module keeps its existing container width (`landing` 600px, `workout` 480px, `meal` 1200px, `calorie`/`fasting` 600px→960px at ≥768px). The extra width on the Duo simply sits empty.
3. **Breakpoint — `min-width: 640px`.** Chosen from the measured viewport table:
   - 382px (folded outer display) and 385px (split view) → top bar. A rail would cost too much of a 382px-wide screen.
   - 669px (inner display, portrait) → **rail**, and the 600px content column still fits beside it (669 − 64 = 605).
   - 871px (Chrome on Duo) and 951px (Safari on Duo, landscape) → rail.
   - 594px (outer display, landscape) → top bar.
   - 640px also matches the breakpoint the calorie/fasting/workout modules already use for their desktop-ish nav, and stays below 871px so Safari and Chrome on iOS agree.
   - Accepted consequence: a *regular* iPhone in landscape (852–956px) also gets the rail. That is deliberate — the rail preserves vertical space on short landscape viewports, which is the same reason iOS moves its controls to the side on wide layouts.

## Global Constraints

- Repo: `/Users/jason/code/personal/habitz/habitz`, branch `main`. `CLAUDE.md` is modified and `DESIGN.md` / `PRODUCT.md` are untracked — **do not commit unrelated files**; stage only the paths each task names.
- Pushing to `main` triggers the GitHub Actions auto-deploy to `rawkit-01` (production). Work on a branch and merge only after review.
- No new runtime dependencies, no build step, no CSS framework. Plain CSS + Jinja only.
- Module Color Sovereignty: `rail.css` may only *consume* colour tokens. Every module declares its own `--rail-*` values in its own `:root`. `rail.css` declares only geometry tokens (`--rail-w`, `--rail-item`, `--rail-inset-right`) and provides `var(--x, fallback)` for everything else.
- `rail.css` must be linked **after** each module's own stylesheet in every template, so rail rules win on equal specificity.
- Touch targets in rail mode: **44×44px minimum** (Apple HIG minimum; the modules currently use 40×40).
- Never size layout from `screen.width`, never hard-code a device width, never branch on user-agent or device name.
- `env(safe-area-inset-*)` is the only way to read insets; the rail pads with `env(safe-area-inset-top)` / `env(safe-area-inset-bottom)` / `env(safe-area-inset-right)` and paints an opaque background behind the inset. The rail hugs the right edge, so the **left** inset belongs to the content area, not to the rail.
- Every icon-only control must have an accessible name (`aria-label`) — in rail mode the visible text is `display: none`, so `aria-label` becomes the only name.
- Modal overlays (`position: fixed; inset: 0`, z-index 1322/1343) intentionally cover the rail; do not lower their z-index.
- Rail mode offsets content by **one rail width on both sides** (`body { padding-left: var(--rail-w); padding-right: … }`) so `margin: 0 auto` columns stay centred on the screen; offsetting the rail side alone leaves them visibly off-centre (found on a real iPhone Duo). Fixed-position chrome other than the header — timer bars, FABs, toasts — is placed against the viewport and needs its own rail-aware offset on the rail side.
- Test command: `venv/bin/python -m pytest tests/ -q` (from the repo root). The repo's venv is `habitz/habitz/venv`.
- After the UI work is finished, run the design detector once (not earlier):
  `.pi/skills/impeccable/scripts/impeccable detect --json landing/static/shared/rail.css landing/templates/index.html budget_tracker/templates/budget/index.html calorie_tracker/templates/base.html fasting_tracker/templates/base.html workout_tracker/templates/base.html meal_planner/templates/base.html`

## Review Focus

Failure modes the design implies but no unit test can catch. Each line is pinned by a task/step below.

1. **Unfolding mid-session.** The Duo changes the viewport from 382 → 669 → 951 without a reload, and fires `resize` events. Anything measured once at load (a JS-computed width, a `100vw` fixed width) will be wrong. *Expected: the rail appears/disappears purely from CSS at 640px; no JS measures the viewport.* → Task 3, verification step.
2. **The 84pt right strip on the folded outer display.** iOS reserves the right edge of the 382px outer display for the camera, clock and Safari buttons; web content stops at 382px, so a page that assumes the full width will look clipped. *Expected: the top bar keeps ≥16px of right padding and the page background extends into the strip (Safari does this for us).* → Task 9, manual verification.
3. **The crease at x ≈ 475.5.** On the inner display in landscape the hinge crosses the centred content column. *Expected: no single interactive control is centred on the crease.* This is a documented limitation of "shell only", not a bug — content reflow is a separate follow-up, and `horizontal-viewport-segments` cannot be relied on while it is feature-flagged. → Task 9, manual verification + follow-up note.
4. **Chrome vs Safari on iOS.** Chrome renders the Duo at 871px, Safari at 951px. *Expected: the rail appears in both.* → Task 3 pins the 640px contract.
5. **Installed PWA vs Safari.** A standalone PWA whose manifest says `"orientation": "portrait-primary"` can never present the landscape/book pose, and iOS 27 may letterbox it. *Expected: every manifest allows rotation.* → Task 1.
6. **Rail icons are the only affordance.** The visible labels are hidden in rail mode, so an unlabelled control is both an accessibility failure and unusable. *Expected: every nav/control in every app has an `aria-label`.* → Tasks 4–8.
7. **Landscape iPhone (852–956px) also gets the rail.** This is a deliberate consequence of the 640px breakpoint, not an accident. *Expected: the rail is usable there — 44px targets, no clipped labels.* → Task 9, manual verification.

---

## File Structure

| File | Responsibility |
|---|---|
| `landing/static/shared/rail.css` | **New.** Shared rail geometry: breakpoint, rail box, item sizing, popover direction. Colour-free. |
| `landing/static/shared/habitz.css` | Existing shared app-switcher styles. Untouched — the rail-mode popover direction is overridden in `rail.css`, which loads later. |
| `landing/templates/index.html` | Landing header markup (`.app-header` family). |
| `budget_tracker/templates/budget/index.html` | Budget header markup (`.app-header` family). |
| `calorie_tracker/templates/base.html` | Calorie nav markup (`.navbar` family). |
| `fasting_tracker/templates/base.html` | Fasting nav markup (`.navbar` family). |
| `workout_tracker/templates/base.html` | Workout nav markup (`.navbar` family, `.nav-brand-wrap`). |
| `meal_planner/templates/base.html` | Meal nav markup (`.navbar` family, icon-only links + dropdown). |
| `landing/static/css/habits.css` | Landing tokens + `.app-header`/`.main-content` rules. |
| `budget_tracker/static/css/budget.css` | Budget tokens + `.app-header` rules. |
| `calorie_tracker/static/css/base.css` | Calorie tokens + `.navbar` rules. |
| `fasting_tracker/static/css/base.css` | Fasting tokens + `.navbar` rules. |
| `workout_tracker/static/css/style.css` | Workout tokens + `.navbar` rules + `.timer-bar`. |
| `meal_planner/static/css/components.css` | Meal tokens + `.navbar`/`.nav-dropdown` rules. |
| `landing/static/manifest.json` | Orientation fix. |
| `calorie_tracker/static/manifest.json` | Orientation fix. |
| `fasting_tracker/static/manifest.json` | Orientation fix. |
| `workout_tracker/static/manifest.json` | Orientation fix. |
| `meal_planner/static/manifest.json` | Orientation fix. |
| `tests/test_responsive_layout.py` | **New.** Cross-app layout contract tests. |

---

### Task 1: Let the installed PWA rotate

The manifests currently pin `"orientation": "portrait-primary"`, so a Habitz PWA added to the iPhone Duo home screen can never present the landscape/book pose the Duo is built around. This is the single cheapest fix in the plan.

**Files:**
- Modify: `landing/static/manifest.json`, `calorie_tracker/static/manifest.json`, `fasting_tracker/static/manifest.json`, `workout_tracker/static/manifest.json`, `meal_planner/static/manifest.json`
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a new test file `tests/test_responsive_layout.py` that later tasks extend. It exposes the module-level constant `MANIFEST_PATHS` (list of repo-relative manifest paths) and the constant `REPO_ROOT` (`pathlib.Path(__file__).resolve().parents[1]`).

- [ ] **Step 1: Create the test file with the failing manifest test**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: FAIL on `landing/static/manifest.json` with "pins orientation to 'portrait-primary'".

- [ ] **Step 3: Change every manifest to `"orientation": "any"`**

In each of the five files, replace the line `"orientation": "portrait-primary",` with `"orientation": "any",`. Change nothing else in the file.

- [ ] **Step 4: Run the test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add tests/test_responsive_layout.py landing/static/manifest.json \
  calorie_tracker/static/manifest.json fasting_tracker/static/manifest.json \
  workout_tracker/static/manifest.json meal_planner/static/manifest.json
git commit -m "feat: allow installed PWA to rotate (iPhone Duo landscape pose)"
```

---

### Task 2: Stop blocking zoom, keep the safe-area viewport

`workout_tracker/templates/base.html:5` sets `user-scalable=no`, which disables pinch-zoom. Apple's guidance is that apps must support the full range of text sizes and user zoom; a fixed-width, zoom-blocked viewport is exactly the "hardcoded screen size" failure the Duo research warns about.

**Files:**
- Modify: `workout_tracker/templates/base.html:5`
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: `REPO_ROOT` from Task 1.
- Produces: module-level constant `TEMPLATE_PATHS` — the six templates that render a header:
  `landing/templates/index.html`, `budget_tracker/templates/budget/index.html`, `calorie_tracker/templates/base.html`, `fasting_tracker/templates/base.html`, `workout_tracker/templates/base.html`, `meal_planner/templates/base.html`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_responsive_layout.py`:

```python
TEMPLATE_PATHS = [
    "landing/templates/index.html",
    "budget_tracker/templates/budget/index.html",
    "calorie_tracker/templates/base.html",
    "fasting_tracker/templates/base.html",
    "workout_tracker/templates/base.html",
    "meal_planner/templates/base.html",
]


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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: FAIL — `test_no_template_blocks_zoom` fails for `workout_tracker/templates/base.html`.

- [ ] **Step 3: Fix the workout viewport meta**

In `workout_tracker/templates/base.html` line 5, change:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover">
```

to:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add tests/test_responsive_layout.py workout_tracker/templates/base.html
git commit -m "fix: allow pinch-zoom in the workout tracker PWA"
```

---

### Task 3: Create the shared rail stylesheet and wire it into all six apps

This task creates the shared geometry and proves it reaches every app. The rail rules are scoped to `@media (min-width: 640px)` and use fallback colours, so on this commit alone the ≥640px layout already shifts to a rail (the per-module `--rail-bg`/`--rail-border` tokens and the template clean-ups from Tasks 4–8 are what finish the job). The branch is intended to merge atomically — `main` auto-deploys on push.

**Files:**
- Create: `landing/static/shared/rail.css`
- Modify: the six templates in `TEMPLATE_PATHS` (add the `<link>` after the module stylesheet)
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: `TEMPLATE_PATHS`, `REPO_ROOT` from Tasks 1–2.
- Produces:
  - `landing/static/shared/rail.css` — the shared rail stylesheet, served at `/static/shared/rail.css`.
  - CSS custom properties consumed by the stylesheet:
    - `--rail-w` — rail width in px. Default `64px`, declared in `rail.css` `:root`; modules may override.
    - `--rail-item` — rail icon target size. Default `44px`, declared in `rail.css` `:root`.
    - `--rail-bg` — rail background (opaque). Consumed as `var(--rail-bg, #0f1117)`; each module declares its own.
    - `--rail-border` — rail hairline colour. Consumed as `var(--rail-border, rgba(255,255,255,0.08))`; each module declares its own.
  - A class `nav-head` — replaces the inline-styled wrapper div that holds the app switcher (and, in landing/budget, the brand). It exists in all six templates after Tasks 4–8; `rail.css` treats it as a wrapper to flatten.

- [ ] **Step 1: Write the failing wiring tests**

Append to `tests/test_responsive_layout.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: FAIL — `FileNotFoundError` for `landing/static/shared/rail.css`.

- [ ] **Step 3: Create `landing/static/shared/rail.css`**

Write exactly this file:

```css
/* Navigation rail — shared geometry for wide viewports (iPhone Duo inner
   display, iPad, desktop).

   Colour is owned by each module (Module Color Sovereignty): this file only
   consumes --rail-bg / --rail-border and never declares them. Geometry
   tokens live here because every module uses the same numbers.

   The rail replaces the horizontal top bar at >=640px. Below that width the
   module's own header/navbar styles are untouched.
*/

:root {
    --rail-w: 64px;
    --rail-item: 44px;
    /* Landscape notch inset: the rail hugs the physical right edge, so it has
       to grow by the inset instead of drawing under it. */
    --rail-inset-right: env(safe-area-inset-right, 0px);
}

@media (min-width: 640px) {
    /* The rail is fixed to the viewport's right edge. Content is offset by
       the same amount on BOTH sides: a column centred with `margin: 0 auto`
       then sits in the middle of the screen, with the rail balanced by an
       equal gutter on the left instead of the page hugging the left edge. */
    body {
        padding-left: var(--rail-w);
        padding-right: calc(var(--rail-w) + var(--rail-inset-right));
    }

    .app-header,
    .navbar {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        left: auto;
        width: calc(var(--rail-w) + var(--rail-inset-right));
        z-index: 200;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        gap: 8px;
        margin: 0;
        max-width: none;
        height: auto;
        padding: calc(env(safe-area-inset-top, 0px) + 12px)
                 var(--rail-inset-right)
                 calc(env(safe-area-inset-bottom, 0px) + 12px)
                 0;
        background: var(--rail-bg, #0f1117);
        border-left: 1px solid var(--rail-border, rgba(255, 255, 255, 0.08));
        border-right: none;
        border-bottom: none;
        backdrop-filter: none;
        -webkit-backdrop-filter: none;
    }

    /* Flatten the header wrappers so their children become rail items.
       No nav link is duplicated, so the two layouts can never disagree. */
    .nav-inner,
    .nav-head,
    .nav-brand-wrap,
    .header-right,
    .user-bar {
        display: contents;
    }

    /* Icon-only stack. flex:1 lets the last item (logout / user menu) be
       pushed to the bottom of the rail with margin-top:auto. */
    .nav-links {
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        gap: 4px;
        flex: 1 1 auto;
        width: 100%;
    }

    /* The logout link / user menu anchors to the bottom of the rail. */
    .nav-logout,
    .nav-dropdown {
        margin-top: auto;
    }

    .nav-link,
    .app-switcher-btn {
        width: var(--rail-item);
        height: var(--rail-item);
        /* No radius override here: every module keeps its own radius token. */
    }

    /* The brand is a rail item too: it gets the same 44x44 touch target as
       every other rail control, whether it renders a text logo (.brand) or
       an icon (.nav-brand). */
    .brand,
    .nav-brand {
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: var(--rail-item);
        min-height: var(--rail-item);
    }

    /* Text labels do not fit in a 64px rail; the icon carries the meaning
       and the accessible name comes from aria-label. */
    .nav-label,
    .nav-title {
        display: none;
    }

    /* Popovers open toward the content (left), not down the rail. */
    .app-switcher-menu {
        top: 0;
        left: auto;
        right: calc(100% + 8px);
    }

    .nav-dropdown-menu {
        top: 0;
        left: auto;
        right: calc(100% + 8px);
    }
}
```

- [ ] **Step 4: Link the stylesheet from all six templates**

In each of the six templates, add the stylesheet link **after** the module's own stylesheet(s), so rail rules win on equal specificity:

- `landing/templates/index.html` — after line 15 (`<link rel="stylesheet" href="/static/shared/habitz.css">`):
  `<link rel="stylesheet" href="/static/shared/rail.css">`
- `calorie_tracker/templates/base.html` — after line 20 (`habitz.css`):
  `<link rel="stylesheet" href="/static/shared/rail.css">`
- `fasting_tracker/templates/base.html` — after line 20 (`habitz.css`):
  `<link rel="stylesheet" href="/static/shared/rail.css">`
- `meal_planner/templates/base.html` — after its last `<link rel="stylesheet">`:
  `<link rel="stylesheet" href="/static/shared/rail.css">`
- `workout_tracker/templates/base.html` — after line 15 (`habitz.css`):
  `<link rel="stylesheet" href="/static/shared/rail.css">`
- `budget_tracker/templates/budget/index.html` — after line 11 (`budget.css`):
  `<link rel="stylesheet" href="/static/shared/rail.css">`

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
git add landing/static/shared/rail.css tests/test_responsive_layout.py \
  landing/templates/index.html budget_tracker/templates/budget/index.html \
  calorie_tracker/templates/base.html fasting_tracker/templates/base.html \
  workout_tracker/templates/base.html meal_planner/templates/base.html
git commit -m "feat: add shared navigation rail stylesheet and wire it into all apps"
```

---

### Task 4: Landing dashboard rail (`.app-header` family)

The landing header is the most complex of the family: an inline-styled wrapper holds the app switcher and the `habitz` brand, and the right side holds a text-only "+ New habit" pill, the username and a text-only "Log out" link. All three must become rail-safe.

**Files:**
- Modify: `landing/templates/index.html:19`, `:52`, `:54-55`
- Modify: `landing/static/css/habits.css` (`:root` at 3-26, `.app-header` at 40, `.brand` at 55, `.btn-new` at 69, `.user-bar` at 85, `.username` at 93, `.logout-link` at 96)
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: `TEMPLATE_PATHS`, `REPO_ROOT`; the `rail.css` geometry and the `--rail-w` / `--rail-item` / `--rail-bg` / `--rail-border` tokens from Task 3.
- Produces:
  - Class `nav-head` on the landing header's left wrapper.
  - Class `btn-new-icon` (SVG, hidden by default) and `btn-new-label` (text span) inside `.btn-new`.
  - Class `logout-icon` (SVG, hidden by default) and `logout-label` (text span) inside `.logout-link`.
  - Landing declares `--rail-bg: #0f1117;` and `--rail-border: var(--border);` in its `:root`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_responsive_layout.py`:

```python
def assert_controls_have_aria_labels(html: str, rel: str) -> None:
    """Every nav/control element must carry an accessible name.

    In rail mode the visible text is display:none, so aria-label is the only
    name the control has.
    """
    import re
    pattern = re.compile(
        r"<(a|button)\b[^>]*class=\"[^\"]*"
        r"(nav-link|logout-link|btn-new|app-switcher-btn)"
        r"[^\"]*\"[^>]*>"
    )
    for match in pattern.finditer(html):
        tag = match.group(0)
        assert "aria-label=" in tag, f"{rel}: control without accessible name -> {tag[:140]}"


class TestLandingRail:
    def test_landing_header_controls_have_accessible_names(self):
        rel = "landing/templates/index.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py::TestLandingRail -v`
Expected: FAIL — the `.btn-new` and `.logout-link` controls have no `aria-label`.

- [ ] **Step 3: Rewrite the landing header markup**

In `landing/templates/index.html`:

(a) Line 19 — replace the inline-styled wrapper:

```html
        <div class="nav-head">
```

(b) Line 52 — give the pill an icon and a label span:

```html
            <a href="/habits/new" class="btn-new" aria-label="New habit" title="New habit">
                <svg class="btn-new-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
                <span class="btn-new-label">+ New habit</span>
            </a>
```

(c) Lines 54-55 — hide the username in rail mode via CSS, and give the logout link an icon:

```html
                <span class="username">{{ user.username or user.email }}</span>
                <a href="/logout" class="logout-link" aria-label="Log out" title="Log out">
                    <svg class="logout-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                    <span class="logout-label">Log out</span>
                </a>
```

- [ ] **Step 4: Add the landing CSS**

In `landing/static/css/habits.css`:

(a) In the `:root` block (lines 3-26), add:

```css
    --rail-bg: #0f1117;
    --rail-border: var(--border);
```

(b) After the `.app-header` rule (line 53), add the `.nav-head` rule:

```css
.nav-head {
    display: flex;
    align-items: center;
    gap: 4px;
}
```

(c) After `.btn-new:hover` (line 83), add:

```css
.btn-new-icon,
.logout-icon {
    display: none;
}
```

(d) Append at the end of the file:

```css
/* ── Navigation rail (>=640px) ─────────────────────── */

@media (min-width: 640px) {
    .app-header {
        /* rail geometry lives in /static/shared/rail.css */
        backdrop-filter: none;
        -webkit-backdrop-filter: none;
    }

    .brand {
        font-size: 0.8125rem;
    }

    .btn-new {
        width: var(--rail-item);
        height: var(--rail-item);
        padding: 0;
        justify-content: center;
        border-radius: var(--radius);
    }

    .btn-new-icon,
    .logout-icon {
        display: block;
    }

    .btn-new-label,
    .logout-label {
        display: none;
    }

    .logout-link {
        display: flex;
        align-items: center;
        justify-content: center;
        width: var(--rail-item);
        height: var(--rail-item);
        border-radius: var(--radius);
        margin-top: auto;
    }

    .username {
        display: none;
    }
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (6 passed).

- [ ] **Step 6: Run the full suite for regressions**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all tests pass, no new failures.

- [ ] **Step 7: Commit**

```bash
git add landing/templates/index.html landing/static/css/habits.css tests/test_responsive_layout.py
git commit -m "feat: navigation rail for the landing dashboard"
```

---

### Task 4b: Landing secondary templates (`history.html`, `habit_form.html`)

The landing app has THREE header-bearing templates, not one: `landing/templates/index.html` (the dashboard), `landing/templates/history.html` (the calendar history) and `landing/templates/habit_form.html` (create/edit habit). Task 3 linked `rail.css` only in `index.html` and Task 4 rewired only `index.html`, so at ≥640px `/history` and `/habits/new` keep the old top bar while `/` shows the rail — the app looks broken as soon as you tap into either page. (Found by the Task 3 review, Risk B.)

`landing/templates/login.html` and `landing/templates/register.html` have no header at all (pre-auth forms) — they are left untouched.

**Files:**
- Modify: `landing/templates/history.html`
- Modify: `landing/templates/habit_form.html`
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: `rail.css` (Task 3 linked it in `index.html` only; this task adds the link to the other two landing templates, AFTER `habitz.css` / `habits.css` so the rail rules win), the `nav-head` wrapper class and the `btn-new-icon` / `logout-icon` / `btn-new-label` / `logout-label` conventions from Task 4.
- Produces: nothing new — both templates become rail-capable.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_responsive_layout.py`:

```python
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
            assert "/static/shared/rail.css" in html, f"{rel} does not link the shared rail stylesheet"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py::TestLandingSecondaryRail -v`
Expected: FAIL — the `.btn-new` / `.logout-link` controls have no `aria-label`, and neither template links `rail.css`.

- [ ] **Step 3: Rewire `history.html`**

- Add `<link rel="stylesheet" href="/static/shared/rail.css">` AFTER the `habitz.css` link (currently line 15).
- Replace the inline-styled wrapper `<div style="display:flex;align-items:center;gap:4px;">` with `<div class="nav-head">` — `habits.css` now carries that styling under the `.nav-head` class (Task 4).
- `<a href="/habits/new" class="btn-new">+ New habit</a>` becomes:

```html
            <a href="/habits/new" class="btn-new" aria-label="New habit" title="New habit">
                <svg class="btn-new-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
                <span class="btn-new-label">+ New habit</span>
            </a>
```

- `<a href="/logout" class="logout-link">Log out</a>` becomes:

```html
                    <a href="/logout" class="logout-link" aria-label="Log out" title="Log out">
                        <svg class="logout-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                        <span class="logout-label">Log out</span>
                    </a>
```

- [ ] **Step 4: Rewire `habit_form.html`**

- Add `<link rel="stylesheet" href="/static/shared/rail.css">` AFTER the `habits.css` link (currently line 9).
- `<a href="/logout" class="logout-link">Log out</a>` gets the same `aria-label` / icon / label-span treatment as in `history.html`.
- The brand link needs no change: it is a direct child of `.app-header`, so the rail already stacks it as an item.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (9 passed).

- [ ] **Step 6: Run the full suite for regressions**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all tests pass, no new failures.

- [ ] **Step 7: Commit**

```bash
git add landing/templates/history.html landing/templates/habit_form.html tests/test_responsive_layout.py
git commit -m "feat: navigation rail for the landing history and habit form pages"
```

---

### Task 5: Budget rail (`.app-header` family)

Budget shares the landing header family but not the shared stylesheet: `budget_tracker/static/css/budget.css:299-425` defines its own `.app-switcher*` rules and the template links only `budget.css` (plus its own inline `<script>` at line 166). The rail must work without pulling in `habitz.css`.

**Files:**
- Modify: `budget_tracker/templates/budget/index.html:15`, `:59-60`
- Modify: `budget_tracker/static/css/budget.css` (`:root` at 5-21, `.app-header` at 34, `.logout-link` at 68)
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: `TEMPLATE_PATHS`, `REPO_ROOT`; `rail.css` geometry and tokens from Task 3; the `nav-head` / `logout-icon` / `logout-label` conventions from Task 4.
- Produces: budget declares `--rail-bg: #0f1117;` and `--rail-border: var(--border);` in its `:root`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_responsive_layout.py`:

```python
class TestBudgetRail:
    def test_budget_header_controls_have_accessible_names(self):
        rel = "budget_tracker/templates/budget/index.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py::TestBudgetRail -v`
Expected: FAIL — the `.logout-link` control has no `aria-label`.

- [ ] **Step 3: Rewrite the budget header markup**

In `budget_tracker/templates/budget/index.html`:

(a) Line 15 — replace the inline-styled wrapper with `<div class="nav-head">`.

(b) Lines 59-60:

```html
            <span class="username">{{ current_user.username or current_user.email }}</span>
            <a href="/logout" class="logout-link" aria-label="Log out" title="Log out">
                <svg class="logout-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                <span class="logout-label">Log out</span>
            </a>
```

- [ ] **Step 4: Add the budget CSS**

In `budget_tracker/static/css/budget.css`:

(a) In the `:root` block (lines 5-21), add:

```css
    --rail-bg: #0f1117;
    --rail-border: var(--border);
```

(b) After the `.app-header` rule (line 47), add:

```css
.nav-head {
    display: flex;
    align-items: center;
    gap: 4px;
}
```

(c) After the `.logout-link:hover` rule (line 74), add:

```css
.logout-icon {
    display: none;
}
```

(d) Append at the end of the file:

```css
/* ── Navigation rail (>=640px) ─────────────────────── */

@media (min-width: 640px) {
    .app-header {
        backdrop-filter: none;
        -webkit-backdrop-filter: none;
    }

    .brand {
        font-size: 0.8125rem;
    }

    .logout-link {
        display: flex;
        align-items: center;
        justify-content: center;
        width: var(--rail-item);
        height: var(--rail-item);
        border-radius: 12px;
        margin-top: auto;
    }

    .logout-icon {
        display: block;
    }

    .logout-label {
        display: none;
    }

    .username {
        display: none;
    }
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (7 passed).

- [ ] **Step 6: Run the full suite for regressions**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add budget_tracker/templates/budget/index.html budget_tracker/static/css/budget.css tests/test_responsive_layout.py
git commit -m "feat: navigation rail for the budget tracker"
```

---

### Task 6: Calorie and Fasting rails (`.navbar` family)

Both modules share the same markup shape: `.navbar > .nav-inner > [inline-styled wrapper > .app-switcher], .nav-brand, .nav-links`. Their `.nav-link` elements carry a `.nav-label` span that is hidden below 640px — so between 640px and 768px, and in the rail, the icons would have no accessible name unless we add `aria-label`.

**Files:**
- Modify: `calorie_tracker/templates/base.html:26`, `:73-84`
- Modify: `fasting_tracker/templates/base.html:28`, `:75-94`
- Modify: `calorie_tracker/static/css/base.css` (`:root` at 6, `.navbar` at 131)
- Modify: `fasting_tracker/static/css/base.css` (`:root` at 6, `.navbar` at 123)
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: `TEMPLATE_PATHS`, `REPO_ROOT`; `rail.css` geometry and tokens from Task 3; the `nav-head` convention from Task 4.
- Produces: calorie and fasting each declare `--rail-bg: #0f1117;` and `--rail-border: rgba(255, 255, 255, 0.06);` in their `:root` (matching their existing `.navbar` background and border).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_responsive_layout.py`:

```python
class TestNavbarFamilyRails:
    def test_calorie_and_fasting_nav_links_have_accessible_names(self):
        for rel in ("calorie_tracker/templates/base.html",
                    "fasting_tracker/templates/base.html"):
            assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py::TestNavbarFamilyRails -v`
Expected: FAIL — the `.nav-link` elements have no `aria-label`.

- [ ] **Step 3: Update the calorie template**

In `calorie_tracker/templates/base.html`:

(a) Line 26 — replace the inline-styled wrapper with `<div class="nav-head">`.

(b) Lines 73-84 — add `aria-label` to each of the three `.nav-link` anchors, matching the visible `.nav-label` text exactly:
- `Dashboard` → `aria-label="Dashboard"`
- `Settings` → `aria-label="Settings"`
- `Log out` → `aria-label="Log out"`

- [ ] **Step 4: Update the fasting template**

In `fasting_tracker/templates/base.html`:

(a) Line 28 — replace the inline-styled wrapper with `<div class="nav-head">`.

(b) Lines 75-94 — add `aria-label` to each of the five `.nav-link` anchors, matching the visible `.nav-label` text exactly: `Fast`, `Micro`, `History`, `Settings`, `Log out`.

- [ ] **Step 5: Add the calorie CSS**

In `calorie_tracker/static/css/base.css`:

(a) In the `:root` block (line 6), add `--rail-bg: #0f1117;` and `--rail-border: rgba(255, 255, 255, 0.06);`.

(b) After the `.navbar` rule (line 140), add:

```css
.nav-head {
    display: flex;
    align-items: center;
    gap: 4px;
}
```

(c) Append at the end of the file:

```css
/* ── Navigation rail (>=640px) ─────────────────────── */

@media (min-width: 640px) {
    .navbar {
        backdrop-filter: none;
        -webkit-backdrop-filter: none;
    }

    .nav-logo {
        width: var(--rail-item);
        height: var(--rail-item);
        align-items: center;
        justify-content: center;
    }
}
```

- [ ] **Step 6: Add the fasting CSS**

Mirror Task 6 Step 5 in `fasting_tracker/static/css/base.css`: same `:root` additions, the same `.nav-head` rule after the `.navbar` rule, and the same `@media (min-width: 640px)` block at the end of the file.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (8 passed).

- [ ] **Step 8: Run the full suite for regressions**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add calorie_tracker/templates/base.html calorie_tracker/static/css/base.css \
  fasting_tracker/templates/base.html fasting_tracker/static/css/base.css \
  tests/test_responsive_layout.py
git commit -m "feat: navigation rail for the calorie and fasting trackers"
```

---

### Task 7: Workout rail (`.navbar` family with `.nav-brand-wrap`)

Workout is the only module whose switcher and brand share a wrapper class (`.nav-brand-wrap`, `workout_tracker/templates/base.html:21-65`) instead of an inline-styled div. `rail.css` already flattens it. The module also owns fixed bottom chrome — the workout timer bar — which must not run under the rail.

**Files:**
- Modify: `workout_tracker/templates/base.html:67-86`
- Modify: `workout_tracker/static/css/style.css` (`:root` at 1-21, `.navbar` at 319, `.timer-bar` at ~240)
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: `TEMPLATE_PATHS`, `REPO_ROOT`; `rail.css` geometry and tokens from Task 3.
- Produces: workout declares `--rail-bg: #0f1117;` and `--rail-border: var(--border);` in its `:root`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_responsive_layout.py`:

```python
class TestWorkoutRail:
    def test_workout_nav_links_have_accessible_names(self):
        rel = "workout_tracker/templates/base.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py::TestWorkoutRail -v`
Expected: FAIL — the `.nav-link` elements have no `aria-label`.

- [ ] **Step 3: Update the workout template**

In `workout_tracker/templates/base.html` lines 67-86, add `aria-label` to each of the five `.nav-link` anchors. The `aria-label` must match the VISIBLE `.nav-label` text (WCAG 2.5.3 "Label in Name"): `Home`, `Programs`, `History`, `Plates`, `Log out`. Note that the fourth anchor's `title` attribute reads `Plate Calculator` while its visible label reads `Plates` — the `aria-label` follows the visible label, and the `title` stays as the tooltip.

- [ ] **Step 4: Add the workout CSS**

In `workout_tracker/static/css/style.css`:

(a) In the `:root` block (lines 1-21), add:

```css
    --rail-bg: #0f1117;
    --rail-border: var(--border);
```

(b) Append at the end of the file:

```css
/* ── Navigation rail (>=640px) ─────────────────────── */

@media (min-width: 640px) {
    .navbar {
        backdrop-filter: none;
        -webkit-backdrop-filter: none;
    }

    .nav-logo {
        width: var(--rail-item);
        height: var(--rail-item);
        align-items: center;
        justify-content: center;
    }

    /* The timer bar is fixed to the viewport, so it would run under the rail
       — now on the right edge. */
    .timer-bar {
        right: calc(var(--rail-w) + var(--rail-inset-right));
    }

    /* The FAB sits bottom-right and would be covered by the rail (z-index
       200); keep it clear of the rail and of the landscape inset. */
    .fab {
        right: calc(20px + var(--rail-w) + var(--rail-inset-right));
    }
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (9 passed).

- [ ] **Step 6: Run the full suite for regressions**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add workout_tracker/templates/base.html workout_tracker/static/css/style.css tests/test_responsive_layout.py
git commit -m "feat: navigation rail for the workout tracker"
```

---

### Task 8: Meal rail (`.navbar` family, icon-only links + user dropdown)

Meal's nav links are already icon-only (they carry a `title` but no text node), so the top bar is already an icon row; the rail is the same row rotated. Two extras: the links need `aria-label` (a `title` alone is a weak accessible name), and the `#userDropdown` menu must open to the left of the rail (the rail is pinned to the right edge) and sit at the bottom of it.

**Files:**
- Modify: `meal_planner/templates/base.html:35`, `:78-95`
- Modify: `meal_planner/static/css/components.css` (`.navbar` at 349, `.nav-dropdown` at 445, `.nav-dropdown-menu` at 449)
- Test: `tests/test_responsive_layout.py`

**Interfaces:**
- Consumes: `TEMPLATE_PATHS`, `REPO_ROOT`; `rail.css` geometry and tokens from Task 3; the `nav-head` convention from Task 4.
- Produces: meal declares `--rail-bg: #0f1117;` and `--rail-border: rgba(255, 255, 255, 0.06);` in its `:root` (matching its existing `.navbar` background and border).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_responsive_layout.py`:

```python
class TestMealRail:
    def test_meal_nav_links_have_accessible_names(self):
        rel = "meal_planner/templates/base.html"
        assert_controls_have_aria_labels((REPO_ROOT / rel).read_text(), rel)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py::TestMealRail -v`
Expected: FAIL — the `.nav-link` elements have no `aria-label`.

- [ ] **Step 3: Update the meal template**

In `meal_planner/templates/base.html`:

(a) Line 35 — replace the inline-styled wrapper with `<div class="nav-head">`.

(b) Lines 78-95 — add `aria-label` to each icon-only control, matching its existing `title` attribute exactly: `Home`, `This Week`, `Shopping`, `My Recipes`. These links have no visible text, so the `title` is the accessible name (WCAG 2.5.3 does not apply — there is no visible label to contain). The `#userDropdown` button already carries `aria-label="More options"` — leave it untouched.

- [ ] **Step 4: Add the meal CSS**

In `meal_planner/static/css/components.css`:

(a) In the meal module's `:root` (the token block in `meal_planner/static/css/base.css`, lines 6-42), add:

```css
    --rail-bg: #0f1117;
    --rail-border: rgba(255, 255, 255, 0.06);
```

(b) After the `.navbar` rule (line 358), add:

```css
.nav-head {
    display: flex;
    align-items: center;
    gap: 4px;
}
```

(c) Append at the end of the file:

```css
/* ── Navigation rail (>=640px) ─────────────────────── */

@media (min-width: 640px) {
    .navbar {
        backdrop-filter: none;
        -webkit-backdrop-filter: none;
    }

    .nav-logo {
        width: var(--rail-item);
        height: var(--rail-item);
        align-items: center;
        justify-content: center;
        font-size: 1.35rem;
    }

    /* Toasts are fixed to the viewport's bottom-right, which the rail now
       occupies — and they sit above it (z-index 1000 > 200). Keep them
       clear of the rail. */
    .toast {
        right: calc(var(--spacing-lg) + var(--rail-w) + var(--rail-inset-right));
    }
}
```

(The user menu's `margin-top: auto` comes from the shared `rail.css`, which
applies it to `.nav-dropdown` for every module.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS (10 passed).

- [ ] **Step 6: Run the full suite for regressions**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add meal_planner/templates/base.html meal_planner/static/css/components.css \
  meal_planner/static/css/base.css tests/test_responsive_layout.py
git commit -m "feat: navigation rail for the meal planner"
```

---

### Task 8b: Give the icon-brand links an accessible name (review finding on Task 6)

The Task 6 review found a WCAG 4.1.2 gap that no later task would close: the four modules that use the `.navbar` family render their brand as an icon plus a `.nav-title` text node, and `rail.css` hides `.nav-title` at ≥640px. In rail mode the brand link therefore has NO accessible name at all — the anchor is nameless, and the link text ("fuel", "fasting", "workout", "Meals") is gone.

The landing and budget modules are unaffected: their `.brand` links carry visible text that the rail never hides, so their name comes from their content.

**Files:**
- Modify: `calorie_tracker/templates/base.html:63-70` (brand anchor + logo SVG)
- Modify: `fasting_tracker/templates/base.html:65-72` (brand anchor + logo SVG)
- Modify: `workout_tracker/templates/base.html:58-64` (brand anchor + logo SVG)
- Modify: `meal_planner/templates/base.html:72-75` (brand anchor + emoji)
- Modify: `tests/test_responsive_layout.py` (the `CONTROL_CLASSES` constant and the helper's docstring)

**Interfaces:**
- Consumes: `assert_controls_have_aria_labels(html, rel)` from Task 4.
- Produces: every `.nav-brand` link has a non-empty accessible name in rail mode.

- [ ] **Step 1: Write the failing test**

In `tests/test_responsive_layout.py`, add `"nav-brand"` to the `CONTROL_CLASSES` tuple:

```python
CONTROL_CLASSES = ("nav-link", "logout-link", "btn-new", "app-switcher-btn", "nav-brand")
```

The shared helper then demands an accessible name from every `.nav-brand` anchor in every template that has one — no new test class is needed: the existing per-module tests (`TestNavbarFamilyRails`, `TestWorkoutRail`, `TestMealRail`) already call the helper on their template.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: FAIL for calorie, fasting, workout and meal — the `.nav-brand` anchors have no `aria-label`.

- [ ] **Step 3: Name the brand links**

In each of the four templates, add an `aria-label` to the `.nav-brand` anchor, equal to the text of the `.nav-title` span inside it:

- `calorie_tracker/templates/base.html` → `aria-label="fuel"`
- `fasting_tracker/templates/base.html` → `aria-label="fasting"`
- `workout_tracker/templates/base.html` → `aria-label="workout"`
- `meal_planner/templates/base.html` → `aria-label="Meals"`

Also mark the decorative logo as such, so it is not announced separately from the link name:

- calorie / fasting / workout: add `aria-hidden="true"` to the `<svg>` inside `.nav-logo` (they already use it on the other decorative SVGs).
- meal: the `.nav-logo` holds an emoji character — add `aria-hidden="true"` to the `<span class="nav-logo">` element.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_responsive_layout.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite for regressions**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add calorie_tracker/templates/base.html fasting_tracker/templates/base.html \
  workout_tracker/templates/base.html meal_planner/templates/base.html \
  tests/test_responsive_layout.py
git commit -m "fix: give the rail brand links an accessible name"
```

---

### Task 9: Verify on real geometry, update the design docs

The unit tests pin contracts; they cannot prove the rail looks right at 382px, 669px and 951px. This task closes the loop and records the decisions so the next session does not re-litigate them.

**Files:**
- Modify: `DESIGN.md` (container model, responsive behaviour, shared-component rule, touch-target floor)
- Modify: `PRODUCT.md` (accessibility section)
- Modify: `CLAUDE.md` (record the rail as a shared component and the Duo breakpoint contract)

**Interfaces:**
- Consumes: everything from Tasks 1-8.
- Produces: documented contracts — the 640px breakpoint, the `--rail-*` token names, the 44px touch-target floor, and the known crease limitation.

- [ ] **Step 0: Add the cross-module rail contract test (review finding on Task 5)**

The Task 5 review noted that nothing asserts the contract every module has to honour: it declares its own `--rail-bg` / `--rail-border`, and it ships a `@media (min-width: 640px)` rail block. Add one test class to `tests/test_responsive_layout.py`:

```python
MODULE_STYLESHEETS = {
    "landing": ("landing/static/css/habits.css", "landing/static/css/habits.css"),
    "budget": ("budget_tracker/static/css/budget.css", "budget_tracker/static/css/budget.css"),
    "calorie": ("calorie_tracker/static/css/base.css", "calorie_tracker/static/css/base.css"),
    "fasting": ("fasting_tracker/static/css/base.css", "fasting_tracker/static/css/base.css"),
    "workout": ("workout_tracker/static/css/style.css", "workout_tracker/static/css/style.css"),
    "meal": ("meal_planner/static/css/base.css", "meal_planner/static/css/components.css"),
}
```

(one tuple per module: the stylesheet that must declare the colour tokens, and the stylesheet that must carry the ≥640px rail block — the meal module keeps its tokens in `base.css` and its navbar rules in `components.css`.)

The test asserts, for every module:
1. the token stylesheet declares `--rail-bg:` and `--rail-border:` inside a `:root { … }` block;
2. the rail stylesheet contains a non-empty `@media (min-width: 640px)` block;
3. the shared `landing/static/shared/rail.css` declares the geometry tokens `--rail-w: 64px` and `--rail-item: 44px`, and never declares `--rail-bg` / `--rail-border` values (Module Color Sovereignty).

- [ ] **Step 1: Verify each pose in Safari 27.1 / the iPhone Duo simulator**

> **Controller note (2026-11-01):** the deploy to production happened before this documentation task, so Step 1's manual Safari check is still outstanding for a human. What HAS been measured, in headless Google Chrome against the real app (a throwaway SQLite DB, 6 viewport widths × 8 pages, asserting header position, rail width, `body` rail-side padding, minimum rail touch-target size, `documentElement.scrollWidth` vs `innerWidth`, and elements past the right edge). *Measured when the rail was still on the left; the user ruling on 2026-11-08 pinned it to the right — the `padding-left` column below now corresponds to `padding-right`, everything else is side-independent:*
>
> | Viewport | Header | Header width | `body` rail-side padding | Smallest rail target | Horizontal overflow |
> |---|---|---|---|---|---|
> | 382px (folded portrait) | `sticky` top bar | 382px (full) | 0 | n/a (top bar) | none |
> | 594px (folded landscape) | `sticky` top bar | 594px (full) | 0 | n/a (top bar) | none |
> | 385px (split view) | `sticky` top bar | 385px (full) | 0 | n/a (top bar) | none |
> | 669px (unfolded portrait) | `fixed` rail | 64px | 64px | 44px | none |
> | 871px (Chrome on iOS) | `fixed` rail | 64px | 64px | 44px | none |
> | 951px (unfolded landscape) | `fixed` rail | 64px | 64px | 44px | none |
>
> Screenshots were reviewed for `/`, `/meals/`, `/calories/`, `/workouts/` and `/budget/` at 669–951px: the rail renders the app switcher, the brand, the module icons and the logout at the bottom, and the top bar is unchanged below 640px.
>
> Known limits of that measurement: Chromium is not Safari; `env(safe-area-inset-*)` is not exercised (it resolves to 0 in Chrome); the crease at x ≈ 475 is not simulated. The real iPhone Duo / Safari 27.1 pass below is therefore still required.

In Xcode 27.1+ use Device Hub → iPhone Duo, and in Safari 27.1 check these viewport widths (DevTools → Responsive, or the simulator's rotate control):

| Check | Width | Expected |
|---|---|---|
| Folded, portrait | 382px | Top bar; no horizontal scrolling; the "+ New habit" pill and "Log out" fully inside the 382px column; nothing under the right-hand system strip |
| Folded, landscape | 594px | Top bar; the top bar's right controls not clipped |
| Unfolded, portrait | 669px | Rail on the right, 64px wide; the 600px content column still fits beside it; the app-switcher menu opens to the left of the rail |
| Unfolded, landscape | 951px | Rail; the crease at x ≈ 475 crosses the content column (accepted limitation, see below) |
| Split view | 385px | Top bar, same as folded portrait |

Also confirm: rotating/folding changes the layout **without a reload** (scroll position and page state preserved) — this is the "measure once at load" failure mode in Review Focus §1.

- [ ] **Step 2: Record the design decisions in `DESIGN.md`**

Update these sections:

- *Container model*: add that at ≥640px the module chrome becomes a fixed 64px right rail (`landing/static/shared/rail.css`) and the content column stays as specified.
- *Responsive behavior*: replace "Primary breakpoint 480px … No tablet-specific layout" with the two-breakpoint model — 480px (username), 640px (rail), 768px (existing wide-container rules).
- *Shared components*: `landing/static/shared/habitz.css` carries the app switcher; `landing/static/shared/rail.css` carries the rail geometry. Colour tokens (`--rail-bg`, `--rail-border`) stay in each module's `:root`.
- *Touch targets*: raise the floor from 40px to 44×44px for rail items, per Apple's HIG minimum.

- [ ] **Step 3: Record the accessibility floor in `PRODUCT.md`**

In the accessibility section, replace "No additional accessibility standard confirmed beyond semantic HTML and ARIA labels" with: WCAG 2.2 AA is the floor; every control has an accessible name (`aria-label` when the label is hidden in rail mode); touch targets are ≥44×44px; the viewport must stay zoomable.

- [ ] **Step 4: Record the deployment + breakpoint facts in `CLAUDE.md`**

Add to the "Shared Conventions" or a new "Responsive Layout" section: the 640px rail breakpoint and the viewport widths it was chosen from (382 / 594 / 669 / 951 CSS px on the Duo; 871px in Chrome on iOS); the `--rail-*` token names; the manifest `orientation: any` requirement for every module; and the known limitation that the Duo's crease crosses the centred content column (content reflow is a separate follow-up, and the Viewport Segments API cannot be relied on while it is behind a Safari feature flag).

- [ ] **Step 5: Run the design detector once**

Run: `.pi/skills/impeccable/scripts/impeccable detect --json landing/static/shared/rail.css landing/templates/index.html budget_tracker/templates/budget/index.html calorie_tracker/templates/base.html fasting_tracker/templates/base.html workout_tracker/templates/base.html meal_planner/templates/base.html`

Expected: the tool reports on the changed targets. Fix anything it flags that is a real defect; if it flags something out of scope, note it rather than expanding this change.

- [ ] **Step 6: Run the full suite one last time**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 7: Commit**

`CLAUDE.md` already carries an unrelated uncommitted change (a 4-line "Hindsight
Memory Bank" section from an earlier session). Commit that on its own first so
the rail change stays reviewable:

```bash
git add CLAUDE.md && git commit -m "docs: add Hindsight memory bank notes"
```

Then commit the rail documentation:

```bash
git add DESIGN.md PRODUCT.md CLAUDE.md
git commit -m "docs: record the navigation rail contract and iPhone Duo layout facts"
```

(`DESIGN.md` and `PRODUCT.md` are still untracked from an earlier session; this
commit adds them for the first time along with the rail contract.)

---

## Follow-ups deliberately out of scope

- **Crease-aware content layout.** On the Duo's inner display in landscape the hinge crosses the centred column. Fixing it needs content that reflows around a fold; the `horizontal-viewport-segments` media query would make it possible but is behind a Safari feature flag, so it cannot be relied on yet. Revisit when it ships.
- **Using the outer display's 84pt side strip.** WebKit states web content cannot currently draw into it (Safari only extends the page background colour). No action is possible from a web app today.
- **Multi-column content on wide viewports.** Deliberately skipped: "shell only" was chosen so the rail is a small, safe diff.
- **Native iOS wrapper.** If Habitz is ever shipped as a real iOS app, the rail is the wrong idiom — Apple's own chrome would occupy the side strip and the inner display would expect a top bar in portrait.
