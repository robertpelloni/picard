# Project Dashboard

## Project Structure

This repository contains the source code for **MusicBrainz Picard**, a cross-platform music tagger written in Python.

### Directory Layout

*   `picard/`: Main application source code.
    *   `plugins/`: Built-in plugins (location of new `artist_discography` plugin).
    *   `ui/`: User interface definitions (Qt).
    *   `webservice/`: Networking and API logic.
    *   `formats/`: Audio file format handlers.
*   `test/`: Unit tests and test data.
*   `docs/`: Documentation.
*   `resources/`: Images, icons, and translation files.
*   `po/`: Localization files.

## Submodules

*No git submodules are currently configured in this repository.*

## Build Information

*   **Version:** 3.0.0.dev9 (Reflected in `VERSION.md` and `picard/__init__.py`)
*   **Build Date:** 2025-12-27
*   **Supported Platforms:** Linux, macOS, Windows
*   **Dependencies:** Python 3.8+, PyQt6 (or PyQt5), Mutagen, libdiscid, aioslsk (optional plugin dep).

## Feature Status Report

| Feature | Status | Notes |
| :--- | :--- | :--- |
| **Core Tagger** | Stable | Existing functionality. |
| **Artist Discography Plugin** | **Completed** | New in v2.14.0. |
| -- Load Discography | ✅ Done | Recursive MB lookup implemented. |
| -- Bandcamp Link | ✅ Done | Metadata + Search fallback. |
| -- Soulseek Search | ✅ Done | Native client. |
| -- Soulseek Download | ✅ Done | File & Folder support. |
| -- Auto-Matching | ✅ Done | Retry-based file moving. |
