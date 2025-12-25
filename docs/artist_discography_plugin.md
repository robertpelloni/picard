# Artist Discography & Soulseek Plugin for Picard

This plugin enhances MusicBrainz Picard with workflows for completing artist discographies. It allows loading all releases for an artist, accessing Bandcamp, and natively searching/downloading missing albums from the Soulseek P2P network.

## Roadmap & Status

| Feature | Status | Implementation Details |
| :--- | :--- | :--- |
| **Discography Loading** | ✅ Done | Fetches release groups/releases from MusicBrainz API (recursive pagination) and loads into Picard. |
| **Bandcamp Integration** | ✅ Done | Extracts `~bandcamp_url` from release relationships; falls back to web search. |
| **Soulseek: Native Search** | ✅ Done | Uses `aioslsk` to search the Soulseek network directly within Picard. |
| **Soulseek: Downloading** | ✅ Done | Supports downloading individual files and **entire folders**. |
| **Soulseek: Auto-Matching** | ✅ Done | Automatically imports downloaded files and targets them to the specific Picard album. |
| **Soulseek: Quality UI** | ✅ Done | Sortable columns (Size, Speed) and color-coded quality indicators (Green=320kbps/Lossless, Red=Low). |
| **Concurrency Support** | ✅ Done | `SoulseekService` handles multiple simultaneous dialogs using context isolation. |

## Installation & Dependencies

This plugin requires the external python library `aioslsk` for Soulseek integration.

```bash
pip install aioslsk
```

*If `aioslsk` is not installed, the Soulseek features will gracefully degrade to a "Copy to Clipboard" helper.*

## Usage

### 1. Loading Discographies
*   **Context Menu:** Right-click a Cluster, Album, or File -> **Plugins** -> **Load Artist Discography**.
*   **Main Menu:** Go to **Tools** -> **Load Artist Discography...** and type an artist name.
*   *Result:* Picard will load empty album structures for all known releases by that artist.

### 2. Bandcamp
*   Right-click an Album -> **Plugins** -> **Open on Bandcamp**.
*   If a Bandcamp relationship exists in MusicBrainz, it opens directly. Otherwise, it performs a search.

### 3. Soulseek Search & Download
1.  **Configure:** Go to **Options** -> **Plugins** -> **Soulseek** and enter your credentials and download folder.
2.  **Search:** Right-click an Album -> **Plugins** -> **Search on Soulseek**.
3.  **Browse Results:**
    *   High quality files (320kbps MP3, FLAC, WAV) appear in **Green/Bold**.
    *   Low quality files (<192kbps) appear in **Red**.
    *   Click headers to sort by Size, Speed, or Queue.
4.  **Download:**
    *   **Single File:** Double-click a row.
    *   **Full Album:** Right-click a row -> **Download Album Folder**.
5.  **Finish:** Once downloaded, files are automatically added to the album in Picard.

## Architecture

*   **Plugin File:** `picard/plugins/artist_discography.py`
*   **Threading:** Uses a singleton `SoulseekService` (inheriting `QThread`) to run the `asyncio` event loop required by `aioslsk`.
*   **Signals:** Uses PyQt signals with a `context` object to route events (results, download completion) to the correct search dialog instance, preventing cross-talk.
