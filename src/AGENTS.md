# Backend Guidance

- Keep Canvas API behavior centralized in `src/services/canvas_client.py` whenever possible.
- Business rules belong in `src/domain`; avoid pushing workflow logic into routes.
- Preserve dry-run branches, per-course result tracking, and operator-readable error messages.
- When changing persistence, keep repository methods explicit and update `docs/database_erd.md` if the schema meaning changes.
- Add or update tests whenever a backend workflow, filter, placeholder, or report contract changes.
