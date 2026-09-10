import pytest
from indexer.parser.filename_parser import FilenameParser


class TestFilenameParser:
    def test_movie_standard_format(self):
        filename = "Inception.2010.1080p.BluRay.x264.Hindi.DD5.1-ESub.mkv"
        parsed = FilenameParser.parse(filename)
        assert parsed.content_type == "movie"
        assert parsed.title.lower() == "inception"
        assert parsed.year == 2010
        assert parsed.quality == "1080p"
        assert parsed.audio is not None and "Hindi" in parsed.audio
        assert parsed.raw_file_name == filename

    def test_movie_with_brackets_and_dual_audio(self):
        filename = "[ChannelName] Interstellar (2014) 720p WEB-DL [Hindi + English] Dual Audio x265.mkv"
        parsed = FilenameParser.parse(filename)
        assert parsed.content_type == "movie"
        assert parsed.title.lower() == "interstellar"
        assert parsed.year == 2014
        assert parsed.quality == "720p"
        assert "Dual Audio" in parsed.audio or "Hindi + English" in parsed.audio

    def test_movie_4k_uhd(self):
        filename = "Avatar.The.Way.of.Water.2022.2160p.UHD.HDR10.HEVC.mkv"
        parsed = FilenameParser.parse(filename)
        assert parsed.content_type == "movie"
        assert "avatar" in parsed.normalized_title
        assert parsed.year == 2022
        assert parsed.quality == "2160p"

    def test_series_standard_s01e01(self):
        filename = "Breaking.Bad.S01E01.720p.BluRay.x264-DEMO.mkv"
        parsed = FilenameParser.parse(filename)
        assert parsed.content_type == "series"
        assert parsed.title.lower() == "breaking bad"
        assert parsed.season_number == 1
        assert parsed.episode_number == 1
        assert parsed.quality == "720p"

    def test_series_with_spaces_and_episode_spelled(self):
        filename = "Stranger Things Season 4 Episode 09 1080p HDRip.mp4"
        parsed = FilenameParser.parse(filename)
        assert parsed.content_type == "series"
        assert parsed.title.lower() == "stranger things"
        assert parsed.season_number == 4
        assert parsed.episode_number == 9
        assert parsed.quality == "1080p"

    def test_series_with_channel_tag_and_underscores(self):
        filename = "@Movies_Channel_Loki_S02E03_1080p_WEB_DL_Hindi_Eng.mkv"
        parsed = FilenameParser.parse(filename)
        assert parsed.content_type == "series"
        assert "loki" in parsed.normalized_title
        assert parsed.season_number == 2
        assert parsed.episode_number == 3
        assert parsed.quality == "1080p"

    def test_series_standalone_episode_number(self):
        filename = "Naruto Shippuden Episode 150 480p.mp4"
        parsed = FilenameParser.parse(filename)
        assert parsed.content_type == "series"
        assert "naruto" in parsed.normalized_title
        assert parsed.season_number == 1
        assert parsed.episode_number == 150
        assert parsed.quality == "480p"

    def test_movie_480p_sd(self):
        filename = "The.Dark.Knight.2008.480p.HDRip.Hindi.mkv"
        parsed = FilenameParser.parse(filename)
        assert parsed.content_type == "movie"
        assert "dark knight" in parsed.normalized_title
        assert parsed.quality == "480p"
        assert parsed.year == 2008

    def test_normalization_consistency(self):
        assert FilenameParser.normalize_title("Money Heist: Korea") == "money heist korea"
        assert FilenameParser.normalize_title("Spider-Man: No Way Home") == "spider man no way home"
        assert FilenameParser.normalize_title("Mr. Robot") == "mr robot"
