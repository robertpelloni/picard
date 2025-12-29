# Changelog

All notable changes to this project will be documented in this file.

## [3.0.0.dev11] - 2025-12-28

### Added
- **Advanced Matching:**
    - Integrated AcoustID fingerprinting for downloaded files.
    - Automatically triggers analysis (`tagger.analyze`) when a file is downloaded and moved to an album if AcoustID is enabled.

## [3.0.0.dev10] - 2025-12-28

### Added
- **Artist Discography Plugin (v1.0):**
    - Load entire artist discographies from MusicBrainz into Picard as empty album structures.
    - Recursive pagination for release group loading.
    - Context menu integration ("Load Artist Discography").
- **Bandcamp Integration:**
    - "Open on Bandcamp" action for albums.
    - Logic to extract Bandcamp URLs from release relationships or fallback to search.
- **Soulseek Integration:**
    - Native Soulseek client using `aioslsk`.
    - Search dialog with quality indicators (bitrate/lossless).
    - Download single files or full album folders.
    - Automatic matching of downloaded files to target Picard albums.
    - Configurable credentials and download path in Options.
- **Global Download Queue:** Added "Soulseek Transfers" menu item to view active background downloads.
- **Improved Auto-Matching:** Added retry logic to ensure downloads are correctly matched to albums.

### Changed
- Updated `PLUGIN_API_VERSIONS` to include 2.12 and 3.0 support.
- Improved plugin compatibility with PyQt5 and PyQt6.
