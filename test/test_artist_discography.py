# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch

# Mock aioslsk
import sys
sys.modules["aioslsk"] = MagicMock()

from picard.plugins import artist_discography
from picard.album import Album
from PyQt6.QtCore import QUrl

class TestArtistDiscographySmoke(unittest.TestCase):

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

if __name__ == "__main__":
    unittest.main()
