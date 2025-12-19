
import sys
import unittest
from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import QApplication

# Initialize QApplication if not already present
if not QApplication.instance():
    app = QApplication(sys.argv)

from test.picardtestcase import PicardTestCase
from picard.metadata import Metadata
from picard.cluster import Cluster
from picard.album import Album
# Import the plugin module
from picard.plugins import artist_discography

class TestArtistDiscographyPlugin(PicardTestCase):

    def setUp(self):
        super().setUp()
        self.plugin = artist_discography

        # Mock Tagger.instance()
        self.tagger_mock = MagicMock()
        self.tagger_mock.webservice.mb_api = MagicMock()
        self.tagger_mock.load_album = MagicMock()
        self.tagger_mock.window = MagicMock()

        self.tagger_patcher = patch('picard.tagger.Tagger.instance', return_value=self.tagger_mock)
        self.tagger_patcher.start()

        self.load_action = self.plugin.LoadDiscography()
        self.open_bandcamp_action = self.plugin.OpenBandcamp()
        self.load_tool = self.plugin.LoadDiscographyTool()

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

    def test_load_discography_logic(self):
        artist_id = 'artist-mbid-123'

        def side_effect(handler, **kwargs):
            offset = kwargs.get('offset', 0)
            total_count = 150
            releases = []
            for i in range(offset, min(offset + 100, total_count)):
                releases.append({'id': f'release-{i}'})

            doc = {
                'release-count': total_count,
                'releases': releases
            }
            handler(doc, None, None)

        self.tagger_mock.webservice.mb_api.browse_releases.side_effect = side_effect

        self.plugin.load_discography(self.tagger_mock, artist_id)

        self.assertEqual(self.tagger_mock.webservice.mb_api.browse_releases.call_count, 2)
        self.assertEqual(self.tagger_mock.load_album.call_count, 150)

    def test_bandcamp_url_handler(self):
        album = MagicMock(spec=Album)
        metadata = Metadata()
        release_node = {
            'relations': [
                {
                    'target-type': 'url',
                    'url': {'resource': 'https://artist.bandcamp.com/album/test'}
                }
            ]
        }
        self.plugin.bandcamp_url_handler(album, metadata, release_node)
        self.assertEqual(metadata['~bandcamp_url'], 'https://artist.bandcamp.com/album/test')

    @patch('picard.plugins.artist_discography.webbrowser2')
    def test_open_bandcamp(self, mock_webbrowser):
        album = MagicMock(spec=Album)
        album.metadata = Metadata()
        album.metadata['~bandcamp_url'] = 'https://example.bandcamp.com'

        self.open_bandcamp_action.callback([album])
        mock_webbrowser.open.assert_called_once_with('https://example.bandcamp.com')

    @patch('picard.plugins.artist_discography.webbrowser2')
    def test_open_bandcamp_fallback(self, mock_webbrowser):
        album = MagicMock(spec=Album)
        album.metadata = Metadata()
        album.metadata['albumartist'] = 'Artist'
        album.metadata['album'] = 'Album'

        self.open_bandcamp_action.callback([album])
        # Expected URL encoding
        expected_url = "https://bandcamp.com/search?q=Artist%20Album%20bandcamp"
        mock_webbrowser.open.assert_called_once_with(expected_url)

    @patch('picard.plugins.artist_discography.QtWidgets.QApplication.clipboard')
    def test_search_soulseek(self, mock_clipboard):
        # Mock clipboard object
        mock_cb_instance = MagicMock()
        mock_clipboard.return_value = mock_cb_instance

        soulseek_action = self.plugin.SearchSoulseek()
        album = MagicMock(spec=Album)
        album.metadata = Metadata()
        album.metadata['albumartist'] = 'Artist'
        album.metadata['album'] = 'Album'

        soulseek_action.callback([album])

        # Verify clipboard was set
        mock_cb_instance.setText.assert_called_once_with("Artist Album")

        # Verify status bar message
        self.tagger_mock.window.statusBar().showMessage.assert_called_once()
        args, _ = self.tagger_mock.window.statusBar().showMessage.call_args
        self.assertIn("Copied to clipboard: Artist Album", args[0])

    @patch('picard.plugins.artist_discography.QtWidgets.QInputDialog.getText')
    @patch('picard.plugins.artist_discography.QtWidgets.QInputDialog.getItem')
    @patch('picard.plugins.artist_discography.load_discography')
    def test_load_discography_tool(self, mock_load, mock_getItem, mock_getText):
        mock_getText.return_value = ('Test Artist', True)
        mock_getItem.return_value = ('Test Artist (US)', True)

        def find_artists_side_effect(handler, **kwargs):
            doc = {
                'artists': [
                    {'name': 'Test Artist', 'id': 'artist-id-1', 'area': {'name': 'US'}},
                ]
            }
            handler(doc, None, None)

        self.tagger_mock.webservice.mb_api.find_artists.side_effect = find_artists_side_effect

        self.load_tool.callback([])

        mock_getText.assert_called_once()
        self.tagger_mock.webservice.mb_api.find_artists.assert_called_once()
        mock_getItem.assert_called_once()

        mock_load.assert_called_once()
        args, _ = mock_load.call_args
        self.assertEqual(args[0], self.tagger_mock)
        self.assertEqual(args[1], 'artist-id-1')

if __name__ == '__main__':
    unittest.main()
