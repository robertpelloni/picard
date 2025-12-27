# Project Roadmap

## Completed Features (v2.14.0 / Plugin v1.0)

- [x] **Discography Loader:**
    - Fetch all release groups for an artist.
    - Fetch representative releases.
    - Load into Picard UI.
- [x] **Bandcamp Integration:**
    - Context menu action.
    - URL extraction from relationships.
- [x] **Soulseek Integration:**
    - Native `aioslsk` integration (Asyncio/QThread).
    - Search UI with sorting and coloring.
    - Download logic (Files/Folders).
    - Auto-clustering of downloaded files.

## Future / Planned Features

- [ ] **Advanced Matching:**
    - Use AcoustID fingerprinting on downloaded files immediately to verify quality.
- [ ] **Soulseek Uploading:**
    - Allow sharing of local library (Release 2.0).
- [x] **Queue Management:**
-    - Global download queue manager UI (Soulseek Transfers dialog).
- [ ] **Protocol Optimization:**
    - Improve Soulseek folder browsing performance (caching).
