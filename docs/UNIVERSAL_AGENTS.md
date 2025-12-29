# Universal LLM Instructions

## Overview
This file serves as the single source of truth for all AI agents (Claude, Gemini, GPT, etc.) working on the MusicBrainz Picard codebase. All model-specific instruction files (`CLAUDE.md`, `GEMINI.md`, etc.) refer to this document.

## Core Directives
1.  **Deep Planning Mode:** Before starting work, fully understand the requirements. Ask clarifying questions.
2.  **Autonomous Execution:** Proceed with implementation, testing, and documentation updates autonomously where possible.
3.  **Documentation First:** Keep `docs/` up to date. Maintain `docs/DASHBOARD.md`, `docs/ROADMAP.md`, `CHANGELOG.md`, and `VERSION.md`.
4.  **Single Source of Truth for Versioning:** `VERSION.md` contains the version number. `picard/__init__.py` must be synced to it. Every build/submission implies a version bump.

## Project Structure
*   `picard/`: Core source code.
*   `picard/plugins/`: Built-in and internal plugins.
*   `ui/`: UI definitions (Qt).
*   `docs/`: Project documentation.
*   `test/`: Unit tests.

## Coding Standards
*   **Language:** Python 3.10+ (as per pyproject.toml).
*   **GUI Framework:** PyQt6 (Preferred), fall back to PyQt5 for compatibility.
*   **Style:** Follow PEP 8. Use `ruff` for linting.
*   **Imports:** Use `try...except ImportError` for PyQt modules to support multiple versions.

## Protocol: Submitting Changes
1.  **Tests:** Run relevant tests (`python3 -m unittest ...`). Use `export QT_QPA_PLATFORM=offscreen` for UI tests.
2.  **Lint:** Run `ruff check` on modified files.
3.  **Version:** Increment `VERSION.md`.
4.  **Changelog:** Update `CHANGELOG.md` with a summary of changes.
5.  **Commit:** Use conventional commit messages (`feat:`, `fix:`, `docs:`).

## Plugin Development
*   Place plugins in `picard/plugins/`.
*   Include metadata (`PLUGIN_NAME`, `PLUGIN_API_VERSIONS`) at the top of the file.
*   Use `picard.extension_points` for registration.
*   Gracefully handle external dependencies (e.g., `aioslsk`).
*   Document the plugin in `docs/`.

## Submodules
*   Current Status: No submodules are currently defined in `.gitmodules`.
*   If added, they must be listed in `docs/DASHBOARD.md`.
