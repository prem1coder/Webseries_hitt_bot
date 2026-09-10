import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from indexer.parser.filename_parser import FilenameParser


class TestFilenameParserUnittest(unittest.TestCase):
    def test_movie_standard_format(self):
        filename = "Inception.2010.1080p.BluRay.x264.Hindi.DD5.1-ESub.mkv"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "movie")
        self.assertEqual(parsed.title.lower(), "inception")
        self.assertEqual(parsed.year, 2010)
        self.assertEqual(parsed.quality, "1080p")
        self.assertIsNotNone(parsed.audio)
        self.assertIn("Hindi", parsed.audio)
        self.assertEqual(parsed.raw_file_name, filename)

    def test_movie_with_brackets_and_dual_audio(self):
        filename = "[ChannelName] Interstellar (2014) 720p WEB-DL [Hindi + English] Dual Audio x265.mkv"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "movie")
        self.assertEqual(parsed.title.lower(), "interstellar")
        self.assertEqual(parsed.year, 2014)
        self.assertEqual(parsed.quality, "720p")
        self.assertTrue("Dual Audio" in parsed.audio or "Hindi + English" in parsed.audio)

    def test_movie_4k_uhd(self):
        filename = "Avatar.The.Way.of.Water.2022.2160p.UHD.HDR10.HEVC.mkv"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "movie")
        self.assertIn("avatar", parsed.normalized_title)
        self.assertEqual(parsed.year, 2022)
        self.assertEqual(parsed.quality, "2160p")

    def test_series_standard_s01e01(self):
        filename = "Breaking.Bad.S01E01.720p.BluRay.x264-DEMO.mkv"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "series")
        self.assertEqual(parsed.title.lower(), "breaking bad")
        self.assertEqual(parsed.season_number, 1)
        self.assertEqual(parsed.episode_number, 1)
        self.assertEqual(parsed.quality, "720p")

    def test_series_with_spaces_and_episode_spelled(self):
        filename = "Stranger Things Season 4 Episode 09 1080p HDRip.mp4"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "series")
        self.assertEqual(parsed.title.lower(), "stranger things")
        self.assertEqual(parsed.season_number, 4)
        self.assertEqual(parsed.episode_number, 9)
        self.assertEqual(parsed.quality, "1080p")

    def test_series_with_channel_tag_and_underscores(self):
        filename = "@Movies_Channel_Loki_S02E03_1080p_WEB_DL_Hindi_Eng.mkv"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "series")
        self.assertIn("loki", parsed.normalized_title)
        self.assertEqual(parsed.season_number, 2)
        self.assertEqual(parsed.episode_number, 3)
        self.assertEqual(parsed.quality, "1080p")

    def test_series_standalone_episode_number(self):
        filename = "Naruto Shippuden Episode 150 480p.mp4"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "series")
        self.assertIn("naruto", parsed.normalized_title)
        self.assertEqual(parsed.season_number, 1)
        self.assertEqual(parsed.episode_number, 150)
        self.assertEqual(parsed.quality, "480p")

    def test_movie_480p_sd(self):
        filename = "The.Dark.Knight.2008.480p.HDRip.Hindi.mkv"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "movie")
        self.assertIn("dark knight", parsed.normalized_title)
        self.assertEqual(parsed.quality, "480p")
        self.assertEqual(parsed.year, 2008)

    def test_series_with_1x05_format(self):
        filename = "Game.of.Thrones.1x05.The.Wolf.and.the.Lion.720p.HDTV.mkv"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "series")
        self.assertIn("game of thrones", parsed.normalized_title)
        self.assertEqual(parsed.season_number, 1)
        self.assertEqual(parsed.episode_number, 5)
        self.assertEqual(parsed.quality, "720p")

    def test_regional_audio_languages(self):
        filename = "Pushpa.2.The.Rule.2024.1080p.Tamil.Telugu.Malayalam.Hindi.mkv"
        parsed = FilenameParser.parse(filename)
        self.assertEqual(parsed.content_type, "movie")
        self.assertIn("pushpa", parsed.normalized_title)
        self.assertIn("Tamil", parsed.audio)
        self.assertIn("Telugu", parsed.audio)
        self.assertIn("Hindi", parsed.audio)

    def test_normalization_consistency(self):
        self.assertEqual(FilenameParser.normalize_title("Money Heist: Korea"), "money heist korea")
        self.assertEqual(FilenameParser.normalize_title("Spider-Man: No Way Home"), "spider man no way home")
        self.assertEqual(FilenameParser.normalize_title("Mr. Robot"), "mr robot")


if __name__ == "__main__":
    unittest.main()
