---
name: manual-qa
description: Build or refresh a manual QA plan for this Canvas panel, then run the lightweight automated checks that support it. Use when the user asks for a test roteiro, regression sweep, UI verification, or a pre-release QA pass.
---

1. Start with `README.md` to confirm the current feature set and operator flow names.
2. Read `docs/manual_test_checklist.md` and update it when a user-facing flow, validation rule, or expected Canvas outcome changed.
3. Run the lightweight validation commands that support manual QA:
   - `conda run -n canvas-bulk-panel pytest -q`
   - `node --check static/js/app.js`
   - `python -m compileall app.py src tests panel_launcher.py`
4. If the change is visual, modal-heavy, or layout-related, also run `npx playwright test`.
5. Report QA in operator terms:
   - what to click
   - what the panel should show
   - what should exist in Canvas
6. If the checklist gained a new scenario, keep it grouped under the existing module names used by the UI.
