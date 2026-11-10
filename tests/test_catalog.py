import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("builder", ROOT / "scripts" / "build_catalog.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class CatalogHelpersTest(unittest.TestCase):
    def test_license_filter_accepts_only_selected_open_licenses(self):
        self.assertTrue(BUILDER.allowed_license("http://creativecommons.org/licenses/publicdomain/"))
        self.assertTrue(BUILDER.allowed_license("https://creativecommons.org/licenses/by/4.0/"))
        self.assertTrue(BUILDER.allowed_license("https://creativecommons.org/licenses/by-sa/4.0/"))
        self.assertFalse(BUILDER.allowed_license("https://creativecommons.org/licenses/by-nc/4.0/"))
        self.assertFalse(BUILDER.allowed_license(""))

    def test_choose_ia_video_prefers_streaming_derivative(self):
        files = [
            {"name": "movie.mp4", "size": "900000000", "format": "MPEG4"},
            {
                "name": "movie_512kb.mp4",
                "size": "50000000",
                "format": "h.264",
                "source": "derivative",
            },
        ]
        self.assertEqual(BUILDER.choose_ia_video(files), "movie_512kb.mp4")

    def test_safe_url_encodes_spaces(self):
        url = BUILDER.safe_url("http://example.com/a movie.mp4")
        self.assertEqual(url, "https://example.com/a%20movie.mp4")


if __name__ == "__main__":
    unittest.main()
