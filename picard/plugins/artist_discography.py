# -*- coding: utf-8 -*-

PLUGIN_NAME = 'Artist Discography & Bandcamp'
PLUGIN_AUTHOR = 'Jules'
PLUGIN_DESCRIPTION = 'Load all albums for an artist and open Bandcamp links.'
PLUGIN_VERSION = '0.1'
PLUGIN_API_VERSIONS = ['2.0', '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.8', '2.9', '2.10', '2.11']
PLUGIN_LICENSE = 'GPL-2.0-or-later'
PLUGIN_LICENSE_URL = 'https://www.gnu.org/licenses/gpl-2.0.html'

from functools import partial
from PyQt6 import QtWidgets, QtCore
from picard import log
from picard.album import Album
from picard.cluster import Cluster
from picard.file import File
from picard.extension_points.item_actions import (
    register_album_action,
    register_cluster_action,
    register_file_action,
)
from picard.extension_points.metadata import register_album_metadata_processor
from picard.extension_points.item_actions import BaseAction
from picard.util import webbrowser2


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

        self.load_discography(artist_id)

    def load_discography(self, artist_id):
        log.info(f"Loading discography for artist ID: {artist_id}")
        self._fetch_page(artist_id, offset=0)

    def _fetch_page(self, artist_id, offset):
        self.tagger.webservice.mb_api.browse_releases(
            partial(self._handle_response, artist_id=artist_id, offset=offset),
            artist=artist_id,
            limit=100,
            offset=offset,
            inc=('media',)
        )

    def _handle_response(self, document, http, error, artist_id, offset):
        if error:
            log.error(f"Load Discography Error: {http.errorString()}")
            return

        releases = document.get('releases', [])
        release_count = document.get('release-count', 0)

        log.info(f"Loaded {len(releases)} releases (Offset: {offset}, Total: {release_count})")

        for release in releases:
            release_id = release['id']
            # Load the album into Picard
            # tagger.load_album handles checking if it's already loaded
            self.tagger.load_album(release_id)

        # Check for next page
        next_offset = offset + len(releases)
        if next_offset < release_count and len(releases) > 0:
            self._fetch_page(artist_id, next_offset)
        else:
            log.info("Finished loading discography.")


register_cluster_action(LoadDiscography())
register_file_action(LoadDiscography())
register_album_action(LoadDiscography())


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


# --- Context Menu Action: Soulseek (Placeholder) ---

class OpenSoulseek(BaseAction):
    NAME = 'Search on Soulseek (Placeholder)'

    def callback(self, objects):
        for item in objects:
            if isinstance(item, Album):
                self._search_soulseek(item)

    def _search_soulseek(self, album):
        artist = album.metadata['albumartist']
        title = album.metadata['album']
        if artist and title:
             msg = f"Soulseek integration is not yet implemented.\n\nWould search for: {artist} - {title}"
             QtWidgets.QMessageBox.information(self.tagger.window, "Soulseek", msg)
        else:
             QtWidgets.QMessageBox.warning(self.tagger.window, "Soulseek", "Missing metadata for search.")

register_album_action(OpenSoulseek())
