---
name: Habitz
description: A unified wellness platform — six sub-apps, three visual families, one shared session.
colors:
  # ── Landing / Habits Hub (dark, blue accent) ──
  bg-dark: "#0f1117"
  surface-dark: "#1a1d27"
  surface-2-dark: "#20232f"
  border-dark: "#2a2d3a"
  border-2-dark: "#363a4f"
  text-dark: "#e8eaf0"
  text-muted-dark: "#8b8fa8"
  text-dim-dark: "#5a5e73"
  accent-blue: "#4a6cf7"
  accent-blue-dim: "rgba(74,108,247,0.12)"
  green: "#22c55e"
  green-dim: "rgba(34,197,94,0.12)"
  red: "#ef4444"
  red-dim: "rgba(239,68,68,0.1)"
  amber: "#f59e0b"
  # ── Workout Tracker (dark, sky-blue accent) ──
  accent-sky: "#4a9eff"
  accent-sky-hover: "#6bb3ff"
  accent-sky-dim: "rgba(74,158,255,0.15)"
  success-teal: "#34d399"
  danger-rose: "#f87171"
  warning-amber: "#fbbf24"
  # ── Fasting Tracker (dark, blue + warm accent) ──
  accent-warm: "#f0a643"
  surface-fast-base: "#0d1117"
  surface-fast-raised: "#161b22"
  # ── Budget Tracker (dark, green/amber/red data) ──
  # (reuses bg-dark family; no unique tokens)
  # ── Calorie Tracker (light, botanical) ──
  cream: "#faf8f5"
  cream-dark: "#f2efe9"
  green-500: "#3d8b41"
  green-600: "#2d6a4f"
  terra: "#d4654a"
  sand: "#e8e2d8"
  stone: "#c4bbb0"
  gray-800: "#2a2724"
  gray-400: "#a09a91"
  # ── Meal Planner (light, farmer's market) ──
  sage: "#87A878"
  terracotta: "#E07A5F"
  honey: "#F4A261"
  cream-mp: "#F8F5F0"
  charcoal: "#3D3D3D"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "3rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.04em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.01em"
rounded:
  sm: "8px"
  md: "12px"
  lg: "14px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent-blue}"
    textColor: "#fff"
    rounded: "{rounded.full}"
    padding: "0.375rem 0.875rem"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-muted-dark}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
  card-dark:
    backgroundColor: "{colors.surface-dark}"
    textColor: "{colors.text-dark}"
    rounded: "{rounded.md}"
    padding: "16px"
  card-light:
    backgroundColor: "{colors.cream}"
    textColor: "{colors.gray-800}"
    rounded: "{rounded.lg}"
    padding: "16px"
  input-dark:
    backgroundColor: "{colors.surface-2-dark}"
    textColor: "{colors.text-dark}"
    rounded: "{rounded.sm}"
    padding: "10px 14px"
---

# Design System: Habitz

## Overview

**Creative North Star: "The Unified Dashboard"**

Habitz is a personal wellness command center, not a consumer product. The visual systems reflect this duality: a dark, utilitarian hub (landing page, workout tracker, fasting tracker, budget) that the owner checks quickly throughout the day, and warm, inviting detail views (meal planner, calorie tracker) for the slower, more contemplative tasks of cooking and meal logging. There is no single visual authority — there are three coexisting families, each tuned to its module's usage context.

**Key Characteristics:**
- **Dark-first hub:** The landing page and workout tracker share a near-black ground (`#0f1117`) with blue accents, optimized for glanceability and low eye strain at the gym or in bed.
- **Light detail surfaces:** Meal planner and calorie tracker use warm cream grounds with botanical greens and terracotta, suited for kitchen/tablet use.
- **App-switcher as spine:** Every module carries the same 2×3 grid switcher in the header — the only true cross-surface component.
- **No shared component library:** Each module authors its own CSS. Shared frontend assets live in `landing/static/shared/`: `habitz.css` carries the app switcher and `rail.css` carries the navigation rail geometry. Colour tokens (`--rail-bg`, `--rail-border`) stay in each module's own `:root` (Module Color Sovereignty).
- **Mobile-native posture:** `env(safe-area-inset-*)`, `100dvh`, sticky headers with `backdrop-filter: blur()`, and large touch targets throughout.

## Colors

### Dark Family (Landing, Workout, Fasting, Budget)

The dark family uses a near-black ground with layered surfaces, all blueshifted to reduce eye strain. Accent colors are functional — green for success/completion, red for errors/destructive, amber for warnings.

- **Void Black** (`#0f1117`): The ground. Used on `body` background in landing, workout, fasting, and budget.
- **Surface** (`#1a1d27`): First elevation. Cards, panels, modal backgrounds.
- **Surface 2** (`#20232f`): Second elevation. Input backgrounds, selected states.
- **Border** (`#2a2d3a`): Subtle dividers. 1px rules between list items, card edges.
- **Border 2** (`#363a4f`): Stronger dividers. Used when more separation is needed.
- **Text** (`#e8eaf0`): Primary text. High contrast on void black.
- **Text Muted** (`#8b8fa8`): Secondary text. Labels, timestamps, placeholders.
- **Text Dim** (`#5a5e73`): Tertiary text. Disabled states, metadata.

**Accents — Dark Family:**
- **Electric Blue** (`#4a6cf7`): Landing page accent. Primary buttons, active rings, focus states.
- **Sky Blue** (`#4a9eff`): Workout tracker accent. Slightly warmer than landing blue — used for primary actions, links, active workout elements.
- **Warm Highlight** (`#f0a643`): Fasting tracker accent. Used for completion states, fasting timer highlights.
- **Signal Green** (`#22c55e` / `#34d399`): Success — habit completion, workout done, fasting goal met.
- **Signal Red** (`#ef4444` / `#f87171`): Error / destructive — failed validation, delete actions.
- **Signal Amber** (`#f59e0b` / `#fbbf24`): Warning — approaching limits, pending states.

### Light Family (Meal Planner, Calorie Tracker)

The light family uses warm cream grounds with botanical greens and terracotta accents. The mood is calmer, more domestic.

- **Cream** (`#faf8f5` / `#f8f5f0`): The ground. Warm, not sterile white.
- **Sand** (`#e8e2d8`): Secondary surfaces. Cards, input backgrounds.
- **Charcoal** (`#3d3d3d` / `#2a2724`): Primary text.
- **Stone** (`#c4bbb0`): Muted text. Labels, metadata.
- **Sage Green** (`#87A878` / `#3d8b41`): Primary accent. Meal planner primary buttons, calorie tracker macro bars.
- **Terracotta** (`#E07A5F` / `#d4654a`): Secondary accent. CTAs, warnings, delete confirmations.
- **Honey Gold** (`#F4A261` / `#d4a03c`): Tertiary accent. Highlights, progress indicators.

### Named Rules

**The Module Color Sovereignty Rule.** Each sub-app owns its accent color. The landing page is blue, workouts are sky-blue, fasting is warm gold, meals are sage, calories are botanical green. Never cross-pollinate accent colors between modules — the app switcher is the only place all five colors may appear together.

**The Ground Inversion Rule.** Dark modules never go light; light modules never go dark. The app switcher and shared header respect the ground of the module they are rendered inside.

## Typography

**Body Font:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif` (dark family) / `DM Sans`, `Outfit`, or `Inter` (light family, depending on module)

**Character:** System-first, utilitarian, optimized for mobile legibility. No display serifs. The light modules use slightly more expressive headings (`Outfit` for display, `DM Sans` for body) but remain firmly in the sans-serif family.

### Hierarchy — Dark Family
- **Display** (700, 3rem, line-height 1, letter-spacing -0.04em): Habit ring center text, large counters.
- **Headline** (700, 1.75rem, line-height 1.1): Page titles.
- **Title** (600, 1.375rem, line-height 1.2): Card titles, section headers.
- **Body** (400, 16px/0.9375rem, line-height 1.5): Default body text. Max ~65ch where constrained.
- **Label** (600, 0.8125rem, line-height 1, letter-spacing 0.01em): Buttons, tags, nav items, timestamps.
- **Micro** (500, 0.625rem–0.75rem, line-height 1): App switcher labels, metadata, unit labels.

### Hierarchy — Light Family
- **Display** (700–800, 40px, line-height 1, letter-spacing -0.03em): Calorie ring center, macro values.
- **Headline** (600, 2rem, line-height 1.3): Page titles (`Quicksand` in meal planner).
- **Title** (500, 1.25rem, line-height 1.3): Card titles.
- **Body** (400, 15px/16px, line-height 1.6): Default text.
- **Label** (500–600, 12px–13px, uppercase, letter-spacing 0.05em): Macro names, section labels.

### Named Rules

**The System Stack Rule.** Dark modules use native system fonts exclusively. Light modules may load Google Fonts (`Outfit`, `DM Sans`, `Quicksand`) but must not load more than two font families per page.

## Layout

**Container Model:** Mobile-first, single-column with a max-width constraint.
- Landing / habits: `max-width: 600px`, centered.
- Workout tracker: `max-width: 480px`, centered.
- Meal planner: `max-width: 1200px`, centered.
- Calorie tracker: `max-width: 600px`, centered.

At `min-width: 640px` the module chrome becomes a fixed 64px left rail (`landing/static/shared/rail.css`); the content column stays as specified above.

**Spacing Rhythm:**
- Base unit: 4px
- Common steps: 8px, 12px, 16px, 24px, 32px
- Page padding: `max(1.25rem, env(safe-area-inset-*))` — respects notch on iOS.
- Card internal padding: 16px (dark), 16–24px (light).

**Header Pattern:** Sticky, `backdrop-filter: blur(12px)` with translucent background (`rgba(15,17,23,0.85)` on dark, `rgba(250,248,245,0.92)` on light). Contains app switcher (left), brand name, and module-specific actions (right).

**Responsive Behavior:**
- Two primary breakpoints: 480px (show/hide username in header) and 640px (the top bar becomes the left rail). 768px carries the existing wide-container rules.
- Landscape phones: reduced padding (`12px`), smaller headers.
- Below 640px the horizontal top bar is unchanged — all modules scale the single-column container.

## Elevation & Depth

**Dark Family:** Shadowless by default. Depth is conveyed through tonal layering (Void → Surface → Surface 2) and subtle borders (`1px solid var(--border)`). Shadows appear only for:
- App switcher menu: `0 8px 40px rgba(0,0,0,0.5)` (structural, to lift above page content).
- Workout cards: `0 2px 8px rgba(0,0,0,0.3)` (minimal lift).

**Light Family:** Soft ambient shadows for cards:
- Default: `0 1px 3px rgba(26,24,22,0.06)`
- Hover: `0 4px 12px rgba(26,24,22,0.08)`
- Elevated: `0 8px 30px rgba(26,24,22,0.1)`

### Named Rules

**The Flat-By-Default Rule.** Surfaces are flat at rest. Shadows appear only as a response to state (hover, open menu) or to lift transient UI above the page. Never use shadows for static card elevation in dark modules.

## Shapes

**Corner Strategy:**
- Cards / panels: `12px` (dark), `12px–16px` (light).
- Buttons: `8px` (dark secondary), `9999px` (dark primary pill), `12px` (light).
- Inputs: `8px` (dark), `8px–16px` (light).
- App switcher menu: `14px`.
- App tiles: `10px`.
- Tags / chips: `99px` (pill).
- Avatars / icon containers: `50%` (circle).

**Border Strategy:**
- Dark: `1px solid rgba(255,255,255,0.08)` for subtle edges; `1px solid var(--border)` for structural dividers.
- Light: `1px solid rgba(0,0,0,0.05)` for card borders; `2px solid` for button outlines.

## Components

### Buttons

**Dark Family — Primary:**
- Shape: Pill (`border-radius: 9999px`).
- Background: Accent color (`#4a6cf7` landing, `#4a9eff` workout).
- Text: White, `0.8125rem`, weight 600.
- Padding: `0.375rem 0.875rem` (compact) or `10px 16px` (standard).
- Hover: `opacity: 0.85` (landing) or background shift (workout).

**Dark Family — Ghost:**
- Shape: `8px` radius.
- Background: Transparent.
- Text: `var(--text-muted)`.
- Hover: Background `rgba(255,255,255,0.06)`, text brightens.

**Light Family — Primary:**
- Shape: `12px` radius, or pill for CTAs.
- Background: Gradient (`135deg`, sage → darker sage) or solid terracotta.
- Text: White, weight 600.
- Hover: `translateY(-2px)` + deeper shadow.

### Cards / Containers

**Dark Card:**
- Background: `var(--surface)` (`#1a1d27`).
- Radius: `12px`.
- Border: None (tonal separation only), or `1px solid var(--border)` for list-group cards.
- Padding: `16px`.
- Shadow: None at rest.

**Light Card:**
- Background: White or `var(--cream)`.
- Radius: `12px–16px`.
- Border: `1px solid rgba(0,0,0,0.05)`.
- Padding: `16px–24px`.
- Shadow: `var(--shadow-sm)` at rest, elevates on hover.

### Inputs / Fields

**Dark Input:**
- Background: `var(--surface-2)` (`#20232f`).
- Border: `1px solid var(--border)`.
- Radius: `8px`.
- Focus: `border-color: var(--accent)`, `box-shadow: 0 0 0 2px var(--accent-dim)`.
- Text: `var(--text)`.
- Placeholder: `var(--text-muted)`.

**Light Input:**
- Background: `var(--cream-dark)` or white.
- Border: `1px solid var(--gray-200)`.
- Radius: `8px–16px`.
- Focus: Border color shifts to accent green.

### Navigation — App Switcher

The app switcher is the shared navigation component (rail aside — see *Navigation Rail* below). Rendered identically across all modules but tinted by the host module's ground.
- Trigger: `40px` square button, `10px` radius, grid-of-four-squares icon.
- Menu: `192px` wide, `14px` radius, dark (`#1a1d27`) with `0 8px 40px rgba(0,0,0,0.5)` shadow.
- Grid: 2×2 tiles, `10px` radius, `14px 8px 12px` padding.
- Icons: `22px` stroke icons, one per module.
- Labels: `0.72rem`, weight 500, below icon.
- Current module tile: `rgba(255,255,255,0.08)` background, white text, no pointer events.

### Navigation Rail (≥640px)

At `min-width: 640px` the header re-lays out as a fixed 64px left rail; below that width the horizontal top bar is unchanged. Geometry is shared in `landing/static/shared/rail.css` (`--rail-w: 64px`, `--rail-item: 44px`, `--rail-inset-left: env(safe-area-inset-left, 0px)`); colour is sovereign per module — each module declares `--rail-bg` and `--rail-border` in its own `:root` and `rail.css` only consumes them. Rail items are `44×44px` minimum (Apple HIG touch-target floor).

Known limitation: the top bar's small touch targets (19–29px) below 640px are a pre-existing issue, out of scope for the rail change.

### Habit Ring (Landing Signature Component)
- SVG circle with `stroke-dasharray` for progress.
- Background stroke: `#2a2d3a`.
- Fill stroke: Gradient (`url(#ringGrad)`), `stroke-linecap: round`.
- Center text: `3rem` weight 700, `-0.04em` tracking.
- Sub-label: `13px` muted.
- Animation: `stroke-dashoffset 0.5s cubic-bezier(0.34,1.56,0.64,1)`.

### Workout Card (Workout Signature Component)
- Full-width card, `12px` radius.
- Background: `#22252f`.
- Today variant: left border `4px solid var(--accent)`.
- Completed variant: left border `4px solid var(--success)`.
- Contains: workout name, exercise list, start/continue button.
- Hover: `background: #2a2d3a`.

### Macro Bars (Calorie Tracker Signature Component)
- Three-column flex layout.
- Each bar: label (uppercase, `12px`, muted) + value (weight 700) above a `6px` track.
- Track: `var(--cream-dark)` background, colored fill.
- Colors: Protein = `#5aaa5e`, Carbs = `#d4a03c`, Fat = `#d4654a`.
- Over-budget: text color switches to terracotta.

## Do's and Don'ts

### Do:
- **Do** respect each module's color sovereignty. Landing is blue, workouts are sky-blue, meals are sage, calories are botanical, fasting is warm gold, budget is data-chromatic (green/amber/red).
- **Do** use `env(safe-area-inset-*)` on all mobile-facing modules. The owner uses this as a PWA on iPhone.
- **Do** keep touch targets at least `44×44px`, per Apple's HIG minimum (rail items must meet this floor). Gym use means sweaty fingers and no precision.
- **Do** use `cubic-bezier(0.34, 1.56, 0.64, 1)` for progress animations (rings, bars). The slight overshoot feels satisfying.
- **Do** write module-specific CSS in that module's `static/css/` directory. The shared `habitz.css` and `rail.css` should only carry the app switcher and the rail geometry.

### Don't:
- **Don't** introduce a third font family into dark modules. System stack only.
- **Don't** use shadows for static cards in dark modules. Tonal layering only.
- **Don't** use the landing page's electric blue (`#4a6cf7`) in the workout tracker. Workouts use sky blue (`#4a9eff`).
- **Don't** mix light and dark grounds within a single module. Each module commits to one family.
- **Don't** add decorative imagery, illustrations, or hero photos. This is a tool, not a marketing site. Icons (SVG stroke) only.
- **Don't** use serif fonts anywhere. The one exception is `DM Serif Display` in the budget tracker for brand voice, and that module should not be the model for others.
