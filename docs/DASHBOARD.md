# Project Dashboard

**Version:** 3.0.0.dev10
**Last Updated:** 2025-12-28

## Project Structure
*   **Root:** Configuration (`pyproject.toml`), Metadata (`VERSION.md`, `CHANGELOG.md`).
*   **picard/:** Core application source code.
    *   `plugins/`: Extension plugins (including `artist_discography.py`).
    *   `ui/`: User interface code.
    *   `webservice/`: Networking and MusicBrainz API interaction.
*   **docs/:** Documentation and Agent Instructions.
*   **test/:** Unit and integration tests.

## Submodules
*   *None currently configured.*

## Build Information
*   **Python:** >= 3.10
*   **Dependencies:** Managed via `requirements.txt` / `pyproject.toml`.
*   **Build System:** `setuptools`.

## Recent Activity
*   **v3.0.0.dev10:** Added Artist Discography & Soulseek Plugin (v1.0).
