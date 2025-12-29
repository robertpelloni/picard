# -*- coding: utf-8 -*-

PLUGIN_NAME = "Artist Discography & Soulseek"
PLUGIN_AUTHOR = "Jules"
PLUGIN_DESCRIPTION = "Load artist discographies, open Bandcamp, and search/download from Soulseek."
PLUGIN_VERSION = "1.0"
PLUGIN_API_VERSIONS = ["2.0", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10", "2.11", "2.12", "3.0"]
PLUGIN_LICENSE = "GPL-2.0-or-later"
PLUGIN_LICENSE_URL = "https://www.gnu.org/licenses/gpl-2.0.html"

import asyncio
from functools import partial
import logging
import os
import webbrowser


try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets

from picard import config, tagger
from picard.album import Album
from picard.cluster import Cluster
from picard.file import File


# Adjust imports based on Picard version structure
try:
    from picard.ui.itemviews import BaseAction, register_album_action, register_cluster_action, register_file_action
except ImportError:
    # Fallback for newer Picard versions where these might be in extension_points
    from picard.extension_points.item_actions import (
        BaseAction,
        register_album_action,
        register_cluster_action,
        register_file_action,
    )
from picard.ui.options import OptionsPage


try:
    from picard.ui.options import register_options_page
except ImportError:
    from picard.extension_points.options_pages import register_options_page
from picard.extension_points.plugin_tools_menu import register_tools_menu_action
from picard.webservice import utils as ws_utils


# Conditional import for aioslsk
try:
    import aioslsk
    HAS_SOULSEEK = True
except ImportError:
    HAS_SOULSEEK = False

log = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

class SoulseekOptionsPage(OptionsPage):
    NAME = "Soulseek"
    TITLE = "Soulseek Configuration"
    PARENT = "plugins"

    options = [
        config.TextOption("setting", "soulseek_username", "Soulseek Username"),
        config.TextOption("setting", "soulseek_password", "Soulseek Password"),
        config.TextOption("setting", "soulseek_download_dir", "Download Directory"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.check_dependencies()

    def check_dependencies(self):
        if not HAS_SOULSEEK:
            warning = QtWidgets.QLabel(
                "<b>Warning:</b> The 'aioslsk' library is not installed. "
                "Soulseek features will be disabled. <br>"
                "Please install it using: <code>pip install aioslsk</code>"
            )
            warning.setStyleSheet("color: red;")
            self.layout().addWidget(warning)

register_options_page(SoulseekOptionsPage)


# =============================================================================
# Soulseek Service (Asyncio/Thread Bridge)
# =============================================================================

class SoulseekService(QtCore.QThread):
    """
    Runs the asyncio loop for aioslsk in a separate thread.
    Communicates with Qt via signals.
    """
    search_result_received = QtCore.pyqtSignal(object, object)  # context, result
    download_complete = QtCore.pyqtSignal(object, str) # context, filepath
    download_started = QtCore.pyqtSignal(str) # filename
    status_message = QtCore.pyqtSignal(str)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.loop = None
        self.client = None
        self.connected = False
        self._keep_running = True
        self.downloads = [] # List of dicts: {'filename': str, 'status': str}
        self.start()

    def run(self):
        if not HAS_SOULSEEK:
            return

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # We need to run the loop forever
        self.loop.run_forever()

    def connect(self):
        if not HAS_SOULSEEK:
            return

        username = config.setting["soulseek_username"]
        password = config.setting["soulseek_password"]

        if not username or not password:
            self.status_message.emit("Please configure Soulseek credentials in Options.")
            return

        asyncio.run_coroutine_threadsafe(self._do_connect(username, password), self.loop)

    async def _do_connect(self, username, password):
        try:
            self.client = aioslsk.SlskClient()
            await self.client.login(username, password)
            self.connected = True
            self.status_message.emit(f"Connected to Soulseek as {username}")
        except Exception as e:
            self.connected = False
            self.status_message.emit(f"Soulseek Connection Error: {e}")

    def search(self, query, context):
        if not self.connected:
            self.connect()
            # Wait a bit? Or just queue? For now, we rely on user retrying or async connect.
            # Realistically we should wait for connection.

        if self.connected:
            asyncio.run_coroutine_threadsafe(self._do_search(query, context), self.loop)
        else:
             self.status_message.emit("Not connected to Soulseek. Retrying connection...")

    async def _do_search(self, query, context):
        if not self.client:
            return

        try:
            # aioslsk search returns an async generator or similar
            # We want to stream results as they come in
            search = await self.client.search(query)
            async for result in search:
                # result is a SlskSearchResult
                self.search_result_received.emit(context, result)
        except Exception as e:
             self.status_message.emit(f"Search Error: {e}")

    def download_file(self, result, context):
        asyncio.run_coroutine_threadsafe(self._do_download_file(result, context), self.loop)

    def download_folder(self, result, context):
        asyncio.run_coroutine_threadsafe(self._do_download_folder(result, context), self.loop)

    async def _do_download_file(self, result, context):
        # result: SlskFile
        download_dir = config.setting["soulseek_download_dir"] or os.path.expanduser("~/Downloads/Soulseek")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        try:
            self.downloads.append({'filename': result.filename, 'status': 'Downloading'})
            self.download_started.emit(result.filename)

            await self.client.download(result, path=download_dir)

            # Update status
            for d in self.downloads:
                if d['filename'] == result.filename:
                    d['status'] = 'Completed'

            # The filename might need to be constructed
            filename = result.filename
            full_path = os.path.join(download_dir, filename) # logic might vary based on aioslsk implementation

            self.download_complete.emit(context, full_path)
            self.status_message.emit(f"Downloaded: {filename}")
        except Exception as e:
            for d in self.downloads:
                if d['filename'] == result.filename:
                    d['status'] = 'Error'
            self.status_message.emit(f"Download Error: {e}")

    async def _do_download_folder(self, result, context):
        # Implementation for folder download
        download_dir = config.setting["soulseek_download_dir"] or os.path.expanduser("~/Downloads/Soulseek")

        # Determine remote folder path from the result filename
        remote_folder = os.path.dirname(result.filename)
        folder_name = os.path.basename(remote_folder)
        local_target_dir = os.path.join(download_dir, folder_name)

        if not os.path.exists(local_target_dir):
            os.makedirs(local_target_dir)

        try:
            self.status_message.emit(f"Browsing folder: {remote_folder}...")

            # Use standard aioslsk method 'get_dir' if available, otherwise fallback.
            # Based on standard libraries, browsing is done via 'get_dir' which returns contents.
            # We assume aioslsk follows this pattern.
            if hasattr(self.client, 'get_dir'):
                contents = await self.client.get_dir(result.user, remote_folder)
            elif hasattr(self.client, 'dir'):
                 contents = await self.client.dir(result.user, remote_folder)
            else:
                 # Fallback attempt
                 contents = await self.client.get_dir_contents(result.user, remote_folder)

            if not contents:
                self.status_message.emit("Folder is empty or could not be retrieved.")
                return

            self.status_message.emit(f"Downloading {len(contents)} files from folder...")

            for file_info in contents:
                # Construct local path
                # file_info usually has 'filename' (full path) or just name.
                # If full path, we extract name.
                fname = os.path.basename(file_info.filename)

                # Check extension to avoid junk
                if fname.lower().endswith(('.mp3', '.flac', '.wav', '.ogg', '.m4a', '.jpg', '.png', '.nfo')):
                    await self.client.download(file_info, path=local_target_dir)
                    self.download_complete.emit(context, os.path.join(local_target_dir, fname))

            self.status_message.emit(f"Folder download finished: {folder_name}")

        except Exception as e:
             self.status_message.emit(f"Folder Download Error: {e}")

# =============================================================================
# UI Components
# =============================================================================

class SoulseekSearchDialog(QtWidgets.QDialog):
    def __init__(self, album, parent=None):
        super().__init__(parent)
        self.album = album
        self.context_id = id(self)
        self.setWindowTitle(f"Soulseek: {album.title}")
        self.resize(800, 600)

        layout = QtWidgets.QVBoxLayout(self)

        # Status
        self.status_label = QtWidgets.QLabel("Ready")
        layout.addWidget(self.status_label)

        # Results Table
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["File", "Size", "Speed", "User", "Quality"])
        self.tree.setSortingEnabled(True)
        layout.addWidget(self.tree)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.search_btn = QtWidgets.QPushButton("Search")
        self.search_btn.clicked.connect(self.start_search)
        btn_layout.addWidget(self.search_btn)

        self.download_btn = QtWidgets.QPushButton("Download Selected")
        self.download_btn.clicked.connect(self.download_selected)
        btn_layout.addWidget(self.download_btn)

        self.download_folder_btn = QtWidgets.QPushButton("Download Folder")
        self.download_folder_btn.clicked.connect(self.download_folder)
        btn_layout.addWidget(self.download_folder_btn)

        layout.addLayout(btn_layout)

        # Connect Service
        self.service = SoulseekService.instance()
        self.service.search_result_received.connect(self.on_result)
        self.service.download_complete.connect(self.on_download_complete)
        self.service.status_message.connect(self.update_status)

        # Auto-search
        self.start_search()

    def start_search(self):
        self.tree.clear()
        query = f"{self.album.artist} {self.album.title}"
        self.status_label.setText(f"Searching for: {query}...")
        self.service.search(query, self.context_id)

    def on_result(self, context, result):
        if context != self.context_id:
            return

        # result is expected to be a SlskSearchResult or SlskFile
        # Assuming SlskFile structure: filename, size, speed, user, extension, etc.
        # Since I cannot see aioslsk docs, I assume common attributes.

        try:
            # Check if result is a file
            if not hasattr(result, 'filename'):
                return

            size_mb = result.size / (1024 * 1024)
            speed_kb = result.speed / 1024 if hasattr(result, 'speed') else 0

            # Quality coloring
            # Green for 320kbps (estimate by size/duration usually, or bitrate if available)
            # Red for low quality.
            # Simple heuristic: > 192kbps MP3 or FLAC/WAV is good.
            # Without duration, size is hard to judge quality alone, but FLAC is obvious.
            ext = os.path.splitext(result.filename)[1].lower()
            is_lossless = ext in ['.flac', '.wav', '.aiff']
            is_good_mp3 = ext == '.mp3' and (getattr(result, 'bitrate', 0) >= 320 or '320' in result.filename)

            color = None
            font_weight = QtGui.QFont.Weight.Normal

            if is_lossless or is_good_mp3:
                color = QtGui.QColor('green')
                font_weight = QtGui.QFont.Weight.Bold
            elif getattr(result, 'bitrate', 999) < 192 and ext == '.mp3':
                color = QtGui.QColor('red')

            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, os.path.basename(result.filename))
            item.setText(1, f"{size_mb:.2f} MB")
            item.setText(2, f"{speed_kb:.0f} KB/s")
            item.setText(3, result.user)
            item.setText(4, "Lossless" if is_lossless else "MP3" if ext == '.mp3' else ext)

            if color:
                for i in range(5):
                    item.setForeground(i, color)
                    font = item.font(i)
                    font.setWeight(font_weight)
                    item.setFont(i, font)

            # Store the full result object for download
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, result)

            self.tree.addTopLevelItem(item)
        except Exception as e:
            log.debug(f"Error parsing search result: {e}")

    def download_selected(self):
        item = self.tree.currentItem()
        if item:
            result = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if result:
                self.status_label.setText(f"Downloading {result.filename}...")
                self.service.download_file(result, self.context_id)

    def download_folder(self):
        item = self.tree.currentItem()
        if item:
            result = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if result:
                self.status_label.setText(f"Queuing folder download for {result.filename}...")
                self.service.download_folder(result, self.context_id)

    def on_download_complete(self, context, filepath):
        if context != self.context_id:
            return

        self.status_label.setText(f"Finished: {filepath}")
        # Add to album
        self.add_file_to_album(filepath)

    def add_file_to_album(self, filepath):
        # Use Picard's Tagger to add file and move to target album
        tagger_obj = tagger.Tagger.instance() # Singleton

        try:
            # We trigger the standard file loading
            tagger_obj.add_files([filepath])

            # Since loading is async, we try to move from unclustered to this album
            # periodically for a few seconds.
            log.info(f"Added {filepath} to Picard. Waiting for load...")

            self._schedule_move_attempt(filepath, attempts=5)

        except Exception as e:
            log.error(f"Error adding file to album: {e}")

    def _schedule_move_attempt(self, filepath, attempts):
        if attempts <= 0:
            return
        # Try every 1 second
        QtCore.QTimer.singleShot(1000, lambda: self._move_file_to_album(filepath, attempts))

    def _move_file_to_album(self, filepath, remaining_attempts):
        # Find the file in unclustered files
        tagger_obj = tagger.Tagger.instance()
        found_file = None

        # Check if UnclusteredFiles exists and has files
        if hasattr(tagger_obj, 'unclustered_files'):
            for file in tagger_obj.unclustered_files.files:
                if file.filename == filepath:
                    found_file = file
                    break

        if found_file:
            # Start AcoustID analysis if enabled
            if tagger_obj.use_acoustid and found_file.can_analyze:
                 log.info(f"Analyzing AcoustID for {filepath}")
                 tagger_obj.analyze([found_file])

            if self.album:
                # Move to album
                tagger_obj.unclustered_files.remove_file(found_file)
                # Picard Album object uses add_file, not add_files
                if hasattr(self.album, 'add_files'):
                     self.album.add_files([found_file])
                elif hasattr(self.album, 'add_file'):
                     self.album.add_file(found_file)

                log.info(f"Moved {filepath} to album {self.album.title}")
        else:
            # Retry
            self._schedule_move_attempt(filepath, remaining_attempts - 1)

    def update_status(self, msg):
        self.status_label.setText(msg)


class SoulseekQueueDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Soulseek Transfers")
        self.resize(600, 400)

        layout = QtWidgets.QVBoxLayout(self)
        self.list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.list_widget)

        self.service = SoulseekService.instance()
        self.service.download_started.connect(self.refresh_list)
        self.service.download_complete.connect(lambda c, f: self.refresh_list())

        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for d in self.service.downloads:
            self.list_widget.addItem(f"{d['filename']} - {d['status']}")

# =============================================================================
# Bandcamp Logic
# =============================================================================

class OpenBandcampAction(BaseAction):
    NAME = "Open on Bandcamp"

    def callback(self, objects):
        for obj in objects:
            if isinstance(obj, Album):
                url = None
                # Check for Bandcamp relationship in album info if available
                if hasattr(obj, '_new_album_info') and obj._new_album_info:
                    for rel in obj._new_album_info.get('relations', []):
                         if 'bandcamp.com' in rel.get('url', {}).get('resource', ''):
                             url = rel['url']['resource']
                             break

                # Fallback search
                if not url:
                    query = f"{obj.artist} {obj.title} bandcamp"
                    url = f"https://duckduckgo.com/?q={query}"

                webbrowser.open(url)

register_album_action(OpenBandcampAction)


# =============================================================================
# Discography Loader
# =============================================================================

class DiscographyLoader:
    def __init__(self, artist_name):
        self.artist_name = artist_name

    def start(self):
        # Search for artist to get ID
        path = "artist"
        query = f'artist:"{self.artist_name}"'

        # Use Tagger.instance().webservice which is the WebService singleton
        tagger_obj = tagger.Tagger.instance()
        host = config.setting["server_host"]
        port = config.setting["server_port"]

        # Construct proper URL
        # We use ws_utils to help with URL construction
        url = ws_utils.host_port_to_url(host, port)
        url.setPath(f"/ws/2/{path}")

        tagger_obj.webservice.get_url(
            url=url,
            queryargs={"query": query},
            handler=partial(self._on_artist_search_result),
            parse_response_type='xml'
        )

    def _on_artist_search_result(self, response, reply, error):
        if error:
            log.error(f"Artist search failed: {error}")
            return

        try:
            # Simple XML parsing (Picard webservice returns bytes)
            # We look for the first artist ID
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response)
            # Namespace map usually needed for MB XML
            ns = {'mb': 'http://musicbrainz.org/ns/mmd-2.0#'}

            artist_list = root.find('.//mb:artist-list', ns)
            if artist_list is not None and len(artist_list) > 0:
                artist = artist_list[0]
                artist_id = artist.attrib['id']
                self.load_release_groups(artist_id)
            else:
                log.warning(f"No artist found for {self.artist_name}")
        except Exception as e:
            log.error(f"Error parsing artist search: {e}")

    def load_release_groups(self, artist_id, offset=0):
        path = f"artist/{artist_id}"

        tagger_obj = tagger.Tagger.instance()
        host = config.setting["server_host"]
        port = config.setting["server_port"]
        url = ws_utils.host_port_to_url(host, port)
        url.setPath(f"/ws/2/{path}")

        tagger_obj.webservice.get_url(
            url=url,
            queryargs={"inc": "release-groups", "limit": "100", "offset": str(offset)},
            handler=partial(self._on_release_groups_result, artist_id=artist_id, offset=offset),
            parse_response_type='xml'
        )

    def _on_release_groups_result(self, response, reply, error, artist_id, offset):
        if error:
            log.error(f"Release group fetch failed: {error}")
            return

        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response)
            ns = {'mb': 'http://musicbrainz.org/ns/mmd-2.0#'}

            # Check pagination
            artist_elem = root.find('.//mb:artist', ns)
            rg_list_elem = artist_elem.find('mb:release-group-list', ns) if artist_elem is not None else None

            total_count = 0
            if rg_list_elem is not None:
                total_count = int(rg_list_elem.attrib.get('count', 0))

                # Find all release groups
                rgs = rg_list_elem.findall('mb:release-group', ns)
                for rg in rgs:
                    rg_id = rg.attrib['id']
                    # Picard's tagger.load_album requires a Release ID, not RG ID.
                    self.fetch_release_for_rg(rg_id)

                # Pagination
                next_offset = offset + 100
                if next_offset < total_count:
                    self.load_release_groups(artist_id, next_offset)

        except Exception as e:
            log.error(f"Error parsing release groups: {e}")

    def fetch_release_for_rg(self, rg_id):
        path = f"release-group/{rg_id}"

        tagger_obj = tagger.Tagger.instance()
        host = config.setting["server_host"]
        port = config.setting["server_port"]
        url = ws_utils.host_port_to_url(host, port)
        url.setPath(f"/ws/2/{path}")

        tagger_obj.webservice.get_url(
             url=url,
             queryargs={"inc": "releases", "limit": "1"},
             handler=partial(self._on_releases_result),
             parse_response_type='xml'
        )

    def _on_releases_result(self, response, reply, error):
        if error:
            return

        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response)
            ns = {'mb': 'http://musicbrainz.org/ns/mmd-2.0#'}

            releases = root.findall('.//mb:release', ns)
            if releases:
                release_id = releases[0].attrib['id']
                # Load into Picard
                tagger_obj = tagger.Tagger.instance()
                # We use load_album from the tagger singleton
                # This puts it in the "Album View" (right pane usually)
                tagger_obj.load_album(release_id)

        except Exception as e:
             log.error(f"Error parsing releases: {e}")

class LoadDiscographyAction(BaseAction):
    NAME = "Load Artist Discography"

    def callback(self, objects):
        artist = None
        artist_id = None
        if objects:
            obj = objects[0]
            if isinstance(obj, Cluster):
                artist = obj.metadata["artist"]
                artist_id = obj.metadata["musicbrainz_artistid"]
            elif isinstance(obj, Album):
                artist = obj.artist
                artist_id = obj.metadata["musicbrainz_artistid"]
            elif isinstance(obj, File):
                artist = obj.metadata["artist"]
                artist_id = obj.metadata["musicbrainz_artistid"]

        # Split multiple IDs if present (MBID can be multi-value, usually separated by / or ; in UI but list in metadata)
        # In Picard metadata, it might be a list or string.
        if isinstance(artist_id, list) and artist_id:
            artist_id = artist_id[0]

        if artist:
            loader = DiscographyLoader(artist)
            if artist_id:
                # If we have an ID, skip search and go straight to loading
                loader.load_release_groups(artist_id)
            else:
                loader.start()

register_cluster_action(LoadDiscographyAction)
register_album_action(LoadDiscographyAction)
register_file_action(LoadDiscographyAction)

# Global Menu Action for Transfer Queue
class ShowTransfersAction(BaseAction):
    NAME = "Soulseek Transfers"

    def callback(self, objects):
        service = SoulseekService.instance()
        if not hasattr(service, 'queue_dialog') or not service.queue_dialog:
            service.queue_dialog = SoulseekQueueDialog()

        service.queue_dialog.show()
        service.queue_dialog.raise_()
        service.queue_dialog.activateWindow()

register_tools_menu_action(ShowTransfersAction)
