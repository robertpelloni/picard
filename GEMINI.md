# Universal LLM Instructions

## Overview
This file contains instructions for AI agents working on the MusicBrainz Picard codebase.

## Coding Standards
*   **Language:** Python 3.8+
*   **GUI Framework:** PyQt6 (Preferred), fall back to PyQt5 for compatibility.
*   **Style:** Follow PEP 8.
*   **Imports:** Use `try...except ImportError` for PyQt modules to support multiple versions.

## Versioning Protocol
*   **Source of Truth:** `VERSION.md` (root directory).
*   **Code Reference:** `picard/__init__.py` must be updated to match `VERSION.md`.
*   **Changelog:** Update `CHANGELOG.md` with every significant feature or fix.
*   **Commit Messages:** Feature: `feat: ...`, Fix: `fix: ...`, Docs: `docs: ...`.

## Documentation
*   **Dashboard:** Maintain `docs/DASHBOARD.md` with project structure and submodule info.
*   **Roadmap:** Maintain `docs/ROADMAP.md` with feature status.

## Plugin Development
*   Place plugins in `picard/plugins/`.
*   Include metadata (`PLUGIN_NAME`, `PLUGIN_API_VERSIONS`) at the top of the file.
*   Use `picard.extension_points` for registration.
*   Gracefully handle external dependencies (e.g., `aioslsk`).

## Testing
*   Run tests using `python3 -m unittest`.
*   For UI tests in headless environments, use `export QT_QPA_PLATFORM=offscreen`.
