---
name: release-version
description: Prepare and publish a Canvas Bulk Panel release. Use when the user asks for a version bump, push, tag, release notes, or GitHub release publication.
---

1. Confirm the working tree and branch state with Git before making release changes.
2. Update `CHANGELOG.md` with a concise release section and update `README.md` if operator-facing behavior changed.
3. Run the release validation stack:
   - `conda run -n canvas-bulk-panel pytest -q`
   - `node --check static/js/app.js`
   - `python -m compileall app.py src tests panel_launcher.py`
   - `npx playwright test` when the release includes UI work
4. Create a focused commit for the release-ready changes.
5. Push `main` before tagging unless the user asked for another branch.
6. Create an annotated tag like `vX.Y.Z`.
7. Publish the GitHub release using the existing helper if available:
   - `release.ps1`
   - or `gh release create ...`
8. In the final handoff, include:
   - commit SHA
   - tag
   - test results
   - release URL
