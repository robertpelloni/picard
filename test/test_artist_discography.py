# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch

# Mock aioslsk
import sys
sys.modules["aioslsk"] = MagicMock()

from picard.plugins import artist_discography
from picard.album import Album
from PyQt6 import QtCore, QtWidgets

class TestArtistDiscographySmoke(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create QApplication once for all tests
        if not QtWidgets.QApplication.instance():
            cls.app = QtWidgets.QApplication([])
        else:
            cls.app = QtWidgets.QApplication.instance()

    def test_imports(self):
        """Test that plugin classes can be imported and instantiated."""
        self.assertTrue(hasattr(artist_discography, "SoulseekService"))
        self.assertTrue(hasattr(artist_discography, "DiscographyLoader"))
        self.assertTrue(hasattr(artist_discography, "OpenBandcampAction"))

    def test_discography_loader_logic(self):
        """Test DiscographyLoader logic calls tagger webservice correctly."""
        loader = artist_discography.DiscographyLoader("Nirvana")
        self.assertEqual(loader.artist_name, "Nirvana")

        # Mock tagger instance and webservice
        with patch("picard.tagger.Tagger.instance") as mock_tagger_instance:
            mock_tagger = MagicMock()
            mock_tagger_instance.return_value = mock_tagger
            mock_webservice = MagicMock()
            mock_tagger.webservice = mock_webservice

            # Mock config
            with patch("picard.config.setting", new={"server_host": "musicbrainz.org", "server_port": 443}):
                # Mock ws_utils
                with patch("picard.webservice.utils.host_port_to_url") as mock_url_builder:
                    mock_url = MagicMock()
                    mock_url_builder.return_value = mock_url

                    loader.start()

                    mock_webservice.get_url.assert_called()
                    # verify arguments roughly
                    args, kwargs = mock_webservice.get_url.call_args
                    self.assertIn("queryargs", kwargs)
                    self.assertIn("handler", kwargs)
                    self.assertEqual(kwargs['parse_response_type'], 'xml')

    def test_acoustid_trigger(self):
        """Test that AcoustID analysis is triggered when a file is loaded."""
        album = MagicMock(spec=Album)
        album.artist = "Nirvana"
        album.title = "Nevermind"
        # Mock add_file (most common in older/standard Picard)
        album.add_file = MagicMock()

        # We need a dialog to access the method, but we mock the service connection
        with patch.object(artist_discography.SoulseekService, 'instance') as mock_service_instance:
            mock_service = MagicMock()
            # Must return a mocked service that has signal attributes with connect methods
            mock_service.search_result_received.connect = MagicMock()
            mock_service.download_complete.connect = MagicMock()
            mock_service.status_message.connect = MagicMock()
            mock_service_instance.return_value = mock_service

            # We mock start_search to prevent network call
            with patch.object(artist_discography.SoulseekSearchDialog, 'start_search'):
                dialog = artist_discography.SoulseekSearchDialog(album)

                # Mock file finding logic
                with patch("picard.tagger.Tagger.instance") as mock_tagger_instance:
                    mock_tagger = MagicMock()
                    mock_tagger_instance.return_value = mock_tagger

                    # Setup mocks for AcoustID check
                    mock_tagger.use_acoustid = True
                    mock_file = MagicMock()
                    mock_file.filename = "/tmp/test.mp3"
                    mock_file.can_analyze = True

                    mock_tagger.unclustered_files.files = [mock_file]

                    # Call the move method
                    dialog._move_file_to_album("/tmp/test.mp3", 1)

                    # Verify analyze was called
                    mock_tagger.analyze.assert_called_with([mock_file])
                    # Verify file was moved
                    mock_tagger.unclustered_files.remove_file.assert_called_with(mock_file)
                    # Check add_file called
                    dialog.album.add_file.assert_called_with(mock_file)

                    dialog.close()

if __name__ == "__main__":
    unittest.main()
