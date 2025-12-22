
import sys
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from PyQt6.QtWidgets import QApplication

# Initialize QApplication if not already present
if not QApplication.instance():
    app = QApplication(sys.argv)

from test.picardtestcase import PicardTestCase
from picard.metadata import Metadata
from picard.cluster import Cluster
from picard.album import Album
from picard.config import get_config
# Import the plugin module
from picard.plugins import artist_discography

class TestArtistDiscographyPlugin(PicardTestCase):

    def setUp(self):
        super().setUp()
        self.config = get_config()
        self.plugin = artist_discography

        # Mock Tagger.instance()
        self.tagger_mock = MagicMock()
        self.tagger_mock.webservice.mb_api = MagicMock()
        self.tagger_mock.load_album = MagicMock()
        self.tagger_mock.add_files = MagicMock()
        self.tagger_mock.window = MagicMock()

        self.tagger_patcher = patch('picard.tagger.Tagger.instance', return_value=self.tagger_mock)
        self.tagger_patcher.start()

        self.load_action = self.plugin.LoadDiscography()
        self.open_bandcamp_action = self.plugin.OpenBandcamp()
        self.load_tool = self.plugin.LoadDiscographyTool()
        self.search_soulseek_action = self.plugin.SearchSoulseek()

        # Reset Service Singleton
        self.plugin.SoulseekService._instance = None

    def tearDown(self):
        self.tagger_patcher.stop()
        super().tearDown()

    def test_load_discography_from_cluster(self):
        cluster = Cluster(name="Test Cluster", artist="Test Artist")
        cluster.metadata['musicbrainz_albumartistid'] = 'artist-mbid-123'

        with patch('picard.plugins.artist_discography.load_discography') as mock_load:
            self.load_action.callback([cluster])
            mock_load.assert_called_once()
            args, _ = mock_load.call_args
            self.assertEqual(args[0], self.tagger_mock)
            self.assertEqual(args[1], 'artist-mbid-123')

    def test_search_soulseek_clipboard_fallback(self,):
        # Ensure credentials are unset
        self.config.setting['soulseek_username'] = ''
        self.config.setting['soulseek_password'] = ''

        with patch('picard.plugins.artist_discography.QtWidgets.QApplication.clipboard') as mock_clipboard:
             mock_cb_instance = MagicMock()
             mock_clipboard.return_value = mock_cb_instance

             album = MagicMock(spec=Album)
             album.metadata = Metadata()
             album.metadata['albumartist'] = 'Artist'
             album.metadata['album'] = 'Album'

             self.search_soulseek_action.callback([album])

             mock_cb_instance.setText.assert_called_once_with("Artist Album")
             self.tagger_mock.window.statusBar().showMessage.assert_called_once()

    def test_options_page(self):
        page = self.plugin.SoulseekOptionsPage()

        # Test Save
        page.username_edit.setText("new_user")
        page.password_edit.setText("new_pass")
        page.dir_edit.setText("/tmp/down")
        page.save()
        self.assertEqual(self.config.setting['soulseek_username'], "new_user")
        self.assertEqual(self.config.setting['soulseek_password'], "new_pass")
        self.assertEqual(self.config.setting['soulseek_download_dir'], "/tmp/down")

    @patch('picard.plugins.artist_discography.SoulSeekClient')
    @patch('picard.plugins.artist_discography.SlskSettings')
    @patch('picard.plugins.artist_discography.HAS_AIOSLSK', True)
    def test_soulseek_service_search(self, mock_settings, mock_client):
        # Mock async behavior
        mock_client_instance = MagicMock() # Use MagicMock instead of AsyncMock for search iterator
        mock_client.return_value = mock_client_instance

        # Mock search results as an async iterator
        async def async_results_iter(query):
            yield MagicMock(filename="song.mp3", user="User1", size=1024, speed=100, slots=True)

        # Ensure that client.search() returns the async iterator directly when called
        mock_client_instance.search.side_effect = lambda q: async_results_iter(q)

        # We need to manually drive the async logic since we can't easily start the QThread loop in unit tests
        # So we test _do_search directly via asyncio.run

        service = self.plugin.SoulseekService.instance()
        service.configure("u", "p", "/d")
        # Ensure client is mocked
        service.client = mock_client_instance

        results_received = []
        service.results_found.connect(lambda res: results_received.extend(res))

        asyncio.run(service._do_search("query"))

        self.assertEqual(len(results_received), 1)
        self.assertEqual(results_received[0].filename, "song.mp3")

    @patch('picard.plugins.artist_discography.SoulSeekClient')
    @patch('picard.plugins.artist_discography.SlskSettings')
    @patch('picard.plugins.artist_discography.HAS_AIOSLSK', True)
    def test_soulseek_service_download(self, mock_settings, mock_client):
        mock_client_instance = AsyncMock()
        mock_client.return_value = mock_client_instance

        # Mock Transfer
        mock_transfer = MagicMock()
        mock_transfer.local_path = "/tmp/song.mp3"
        # Setup state mocks
        state_mock = MagicMock()
        state_mock.is_complete = True # Immediately complete
        state_mock.is_aborted = False
        state_mock.is_failed = False
        mock_transfer.state = state_mock

        mock_client_instance.transfer_manager.download.return_value = mock_transfer

        service = self.plugin.SoulseekService.instance()
        service.configure("u", "p", "/d")
        # Ensure client is mocked
        service.client = mock_client_instance

        completed_path = []
        service.download_complete.connect(lambda p: completed_path.append(p))

        asyncio.run(service._do_download("user", "file"))

        self.assertEqual(completed_path[0], "/tmp/song.mp3")

if __name__ == '__main__':
    unittest.main()
