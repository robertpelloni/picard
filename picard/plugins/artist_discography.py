# -*- coding: utf-8 -*-

PLUGIN_NAME = 'Artist Discography & Bandcamp'
PLUGIN_AUTHOR = 'Jules'
PLUGIN_DESCRIPTION = 'Load all albums for an artist and open Bandcamp links.'
PLUGIN_VERSION = '0.2'
PLUGIN_API_VERSIONS = ['2.9', '2.10', '2.11']
PLUGIN_LICENSE = 'GPL-2.0-or-later'
PLUGIN_LICENSE_URL = 'https://www.gnu.org/licenses/gpl-2.0.html'

"""
Artist Discography & Bandcamp Plugin

This plugin provides tools to load an artist's full discography from MusicBrainz and open Bandcamp pages.

Features:
- **Load Artist Discography**: Context menu action (on Cluster/File/Album) to fetch all releases for the artist from MusicBrainz and load them into Picard.
- **Load Artist Discography (Tool)**: Main menu tool to search for an artist by name and load their discography.
- **Open on Bandcamp**: Context menu action (on Album) to open the Bandcamp page for the release. It uses Bandcamp URLs found in MusicBrainz relationships or falls back to a search.
- **Soulseek Placeholder**: A placeholder action for future Soulseek integration.
"""

from functools import partial
from PyQt6 import QtWidgets, QtCore
from picard import log
from picard.tagger import Tagger
from picard.album import Album
from picard.cluster import Cluster
from picard.file import File
from picard.extension_points.item_actions import (
    register_album_action,
    register_cluster_action,
    register_file_action,
    BaseAction
)
from picard.extension_points.metadata import register_album_metadata_processor
from picard.extension_points.plugin_tools_menu import register_tools_menu_action
from picard.util import webbrowser2


# --- Shared Loading Logic ---

def load_discography(tagger, artist_id):
    """
    Load all releases for a given artist ID into Picard.
    Initiates a recursive fetch of release pages from MusicBrainz.
    """
    log.info(f"Loading discography for artist ID: {artist_id}")
    _fetch_page(tagger, artist_id, offset=0)

def _fetch_page(tagger, artist_id, offset):
    tagger.webservice.mb_api.browse_releases(
        partial(_handle_response, tagger=tagger, artist_id=artist_id, offset=offset),
        artist=artist_id,
        limit=100,
        offset=offset,
        inc=('media',)
    )

def _handle_response(document, http, error, tagger, artist_id, offset):
    if error:
        log.error(f"Load Discography Error: {http.errorString()}")
        return

    releases = document.get('releases', [])
    release_count = document.get('release-count', 0)

    log.info(f"Loaded {len(releases)} releases (Offset: {offset}, Total: {release_count})")

    for release in releases:
        release_id = release['id']
        tagger.load_album(release_id)

    # Check for next page
    next_offset = offset + len(releases)
    if next_offset < release_count and len(releases) > 0:
        _fetch_page(tagger, artist_id, next_offset)
    else:
        log.info("Finished loading discography.")


# --- Metadata Processor for Bandcamp URLs ---

def bandcamp_url_handler(album, metadata, release_node):
    """Extract Bandcamp URLs from release relations and store in metadata."""
    if not release_node:
        return

    relations = release_node.get('relations', [])
    for relation in relations:
        if relation.get('target-type') == 'url':
            url_resource = relation.get('url', {}).get('resource', '')
            if 'bandcamp.com' in url_resource:
                # Store the first one found
                metadata['~bandcamp_url'] = url_resource
                return

register_album_metadata_processor(bandcamp_url_handler)


# --- Context Menu Action: Load Discography ---

class LoadDiscography(BaseAction):
    NAME = 'Load Artist Discography'

    def callback(self, objects):
        if not objects:
            return

        item = objects[0]
        artist_id = None

        if isinstance(item, Cluster):
            # Cluster metadata is a bit different, checking common fields
            if item.metadata['musicbrainz_albumartistid']:
                artist_id = item.metadata['musicbrainz_albumartistid']
        elif isinstance(item, File):
            artist_id = item.metadata['musicbrainz_albumartistid'] or item.metadata['musicbrainz_artistid']
        elif isinstance(item, Album): # Also allow running from an existing Album
             artist_id = item.metadata['musicbrainz_albumartistid']

        # Handle multi-value IDs (take the first one)
        if isinstance(artist_id, list):
            artist_id = artist_id[0]

        # Split if multiple IDs in string
        if artist_id and ';' in artist_id:
             artist_id = artist_id.split(';')[0].strip()

        if not artist_id:
            log.error("Load Discography: No Artist ID found in selected item.")
            return

        load_discography(Tagger.instance(), artist_id)


register_cluster_action(LoadDiscography())
register_file_action(LoadDiscography())
register_album_action(LoadDiscography())


# --- Main Menu Action: Load Discography ---

class LoadDiscographyTool(BaseAction):
    NAME = 'Load Artist Discography...'

    def callback(self, objects):
        # objects is ignored for main menu actions usually
        tagger = Tagger.instance()
        text, ok = QtWidgets.QInputDialog.getText(
            tagger.window,
            "Load Discography",
            "Enter Artist Name:"
        )
        if ok and text:
            self.search_artist(text)

    def search_artist(self, query):
        Tagger.instance().webservice.mb_api.find_artists(
            self._handle_search_response,
            query=query,
            limit=10
        )

    def _handle_search_response(self, document, http, error):
        tagger = Tagger.instance()
        if error:
            log.error(f"Artist Search Error: {http.errorString()}")
            QtWidgets.QMessageBox.critical(tagger.window, "Error", f"Search failed: {http.errorString()}")
            return

        artists = document.get('artists', [])
        if not artists:
            QtWidgets.QMessageBox.information(tagger.window, "Load Discography", "No artists found.")
            return

        # Prepare list for selection
        items = []
        for artist in artists:
            name = artist.get('name', 'Unknown')
            disambiguation = artist.get('disambiguation', '')
            area = artist.get('area', {}).get('name', '')
            desc = f"{name}"
            details = []
            if disambiguation: details.append(disambiguation)
            if area: details.append(area)
            if details:
                desc += f" ({', '.join(details)})"
            items.append(desc)

        item, ok = QtWidgets.QInputDialog.getItem(
            tagger.window,
            "Select Artist",
            "Choose an artist:",
            items,
            0,
            False
        )

        if ok and item:
            index = items.index(item)
            selected_artist = artists[index]
            artist_id = selected_artist['id']
            load_discography(tagger, artist_id)

register_tools_menu_action(LoadDiscographyTool())


# --- Context Menu Action: Open Bandcamp ---

class OpenBandcamp(BaseAction):
    NAME = 'Open on Bandcamp'

    def callback(self, objects):
        for item in objects:
            if isinstance(item, Album):
                self._open_album(item)

    def _open_album(self, album):
        url = album.metadata['~bandcamp_url']
        if url:
            log.info(f"Opening Bandcamp URL: {url}")
            webbrowser2.open(url)
        else:
            # Fallback search
            artist = album.metadata['albumartist']
            title = album.metadata['album']
            if artist and title:
                search_query = f"{artist} {title} bandcamp"
                # Simple google search or bandcamp search
                encoded_query = QtCore.QUrl.toPercentEncoding(search_query).data().decode('utf-8')
                url = f"https://bandcamp.com/search?q={encoded_query}"
                log.info(f"Bandcamp URL not found, searching: {url}")
                webbrowser2.open(url)
            else:
                log.warning("Cannot search Bandcamp: Missing artist or album title.")

register_album_action(OpenBandcamp())


# --- Context Menu Action: Soulseek ---

class SearchSoulseek(BaseAction):
    NAME = 'Search on Soulseek'

    def callback(self, objects):
        for item in objects:
            if isinstance(item, Album):
                self._search_soulseek(item)

    def _search_soulseek(self, album):
        tagger = Tagger.instance()
        artist = album.metadata['albumartist']
        title = album.metadata['album']
        if artist and title:
             query = f"{artist} {title}"
             QtWidgets.QApplication.clipboard().setText(query)
             tagger.window.statusBar().showMessage(f"Copied to clipboard: {query}", 5000)
        else:
             log.warning("Soulseek search: Missing artist or album title.")

register_album_action(SearchSoulseek())
