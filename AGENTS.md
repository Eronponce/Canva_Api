# Codex Repo Guidance

## First Read

1. `README.md` for product scope, setup, and current user-facing flows.
2. `docs/manual_test_checklist.md` when a change affects behavior that should be validated manually.
3. `docs/ui_audit_action_plan.md` when adjusting layout, density, accessibility, or modal flows.
4. `docs/database_erd.md` before changing persistence or reporting.

## Core Rules

- Use only official Canvas API endpoints. Do not invent routes or browser automation fallbacks.
- Keep the UI compact, dark, and operationally clear. Avoid horizontal overflow and avoid reintroducing noisy technical identifiers into primary operator views.
- Preserve safe placeholder support across frontend, backend, previews, and validation. If a placeholder is added or removed, update every layer together.
- Keep dry-run behavior, per-course error reporting, and CSV/report flows intact when touching batch operations.
- Prefer changes that keep local SQLite support working even if MySQL is also supported.

## Repo Routing

- `src/services/canvas_client.py`: official Canvas API calls, pagination, retries, and request details.
- `src/domain/`: business rules for announcements, inbox, inactive students, recurrence, settings, and reports.
- `src/database/`: models, repositories, and persistence logic.
- `templates/index.html`: screen structure and modal markup.
- `static/js/app.js`: UI state, validation, previews, modal flows, and client rendering.
- `static/css/styles.css`: theme, spacing, table density, responsive behavior, and interaction polish.

## Validation Commands

- `conda run -n canvas-bulk-panel pytest -q`
- `node --check static/js/app.js`
- `python -m compileall app.py src tests panel_launcher.py`
- `npx playwright test`

## Documentation Expectations

- Update `README.md` when operator-facing behavior changes.
- Update `docs/manual_test_checklist.md` when a manual flow changes or a new feature needs QA coverage.
- Update `CHANGELOG.md` when preparing a release-worthy change.

## Skills In This Repo

- `.agents/skills/manual-qa`: use for manual regression planning and UI/QA sweeps.
- `.agents/skills/release-version`: use for version bump, release prep, tag, and publish flow.
