# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: solo user (owner/developer), daily personal wellness tracking. Secondary: household members invited to shared meal planner.

## Product Purpose

A unified wellness dashboard that replaces multiple SaaS apps with one self-hosted, API-first platform. The user owns their data, controls configuration, and interacts with the system via web UI, JSON API, and iOS Shortcuts.

Success means: one login, one database, all wellness data in one place — habits, meals, calories, fasting, workouts, and budget — with minimal friction during real-world use (especially at the gym).

## Positioning

Self-hosted, configurable wellness platform where the user owns their data. Unlike SaaS alternatives, Habitz exposes a JSON API for every module, supports iOS Shortcuts automation, integrates with Peloton and Apple Health, and runs on hardware the user controls.

## Operating Context

- Used daily via mobile (PWA, iOS home screen) and desktop
- At the gym: workout logging must require as few taps/clicks as possible
- In the kitchen: meal planning and recipe import
- Morning/evening: habit dashboard check-in, fasting timer, calorie logging
- Budget tracking pulls from Google Sheets weekly
- iOS Shortcut fetches workout data and logs to Apple Health (Peloton rides excluded — app handles those natively)

## Capabilities and Constraints

- Unified SQLite database shared across all modules via `DispatcherMiddleware`
- Shared session cookie (`habitz_session`) — login once, access all modules
- Flask application factory pattern; each module has its own `create_app()`
- Server-rendered Jinja2 + vanilla JS IIFEs + custom CSS (no frontend framework)
- Timezone-aware: all user-facing dates use `ZoneInfo(user.timezone)`
- Workout programs follow a fixed rotation: Push → Cardio → Pull → Cardio → Legs → Cardio
- Peloton workouts auto-import daily; traditional workouts logged manually
- Recipe URLs scraped with MiMo-V2.5 when schema.org fails
- Budget tracker requires Google service account + Sheet ID

## Brand Commitments

- Name: "habitz" (lowercase)
- Dark theme: `#0f1117` background, white text
- App switcher grid UI pattern (5 modules)
- PWA: manifest, icons (180/192/512), apple-mobile-web-app-capable
- No external design system — custom CSS per module with shared `habitz.css`

## Evidence on Hand

- Live production at `https://habitz.fit`
- No marketing assets, testimonials, or case studies (personal tool, not a product for sale)

## Product Principles

1. **Self-hosted first** — data stays on hardware the user controls
2. **API-everything** — every module exposes JSON endpoints for automation
3. **Gym-speed** — workout logging must be faster than opening a notes app
4. **Unified over perfect** — one shared DB and session beats modular isolation
5. **Own your data** — exports, integrations, and migrations are first-class

## Accessibility & Inclusion

Mobile-first design with `viewport-fit=cover` and `env(safe-area-inset-*)` for notched devices. WCAG 2.2 AA is the floor: every control has an accessible name (`aria-label` when the visible label is hidden in rail mode), touch targets are ≥44×44px, and the viewport must stay zoomable (pinch-zoom available — no `user-scalable=no`).
