import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedMediaInfo:
    raw_file_name: str
    title: str
    normalized_title: str
    content_type: str  # 'movie' or 'series'
    year: Optional[int] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    episode_title: Optional[str] = None
    quality: Optional[str] = None
    audio: Optional[str] = None


class FilenameParser:
    EXTENSIONS = r"\.(?:mkv|mp4|avi|webm|mov|flv|wmv|m4v|ts)$"

    # Series season & episode patterns (robust against underscores and brackets)
    SERIES_PATTERNS = [
        # S01E02, S1E2, S01.E02, S01_E02, S01 - E02
        re.compile(r"(?i)(?:^|[\s\._\-\(\[])S(?P<season>\d{1,2})[\s\.\-_]*E(?P<episode>\d{1,3})(?:$|[\s\._\-\)\]])"),
        # Season 1 Episode 2, Season 01 Ep 02, Season 1 Ep2
        re.compile(r"(?i)(?:^|[\s\._\-\(\[])Season[\s\.\-_]*(?P<season>\d{1,2})[\s\.\-_]*(?:Episode|Ep)[\s\.\-_]*(?P<episode>\d{1,3})(?:$|[\s\._\-\)\]])"),
        # 1x02, 01x02
        re.compile(r"(?i)(?:^|[\s\._\-\(\[])(?P<season>\d{1,2})x(?P<episode>\d{1,3})(?:$|[\s\._\-\)\]])"),
        # Ep 02 or Episode 02
        re.compile(r"(?i)(?:^|[\s\._\-\(\[])(?:Episode|Ep)[\s\.\-_]*(?P<episode>\d{1,3})(?:$|[\s\._\-\)\]])"),
        # S01 Complete, Season 1 Complete
        re.compile(r"(?i)(?:^|[\s\._\-\(\[])(?:S|Season)[\s\.\-_]*(?P<season>\d{1,2})[\s\.\-_]*(?:Complete|Pack|All\s*Episodes)(?:$|[\s\._\-\)\]])"),
    ]

    # Quality extraction patterns
    QUALITY_PATTERNS = [
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(2160p|4k|uhd)(?:$|[\s\._\-\)\]])"), "2160p"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(1080p|1080i|fhd)(?:$|[\s\._\-\)\]])"), "1080p"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(720p|hd)(?:$|[\s\._\-\)\]])"), "720p"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(480p|576p|360p|sd)(?:$|[\s\._\-\)\]])"), "480p"),
    ]

    # Audio patterns
    AUDIO_PATTERNS = [
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Dual[\s\.\-_]*Audio)(?:$|[\s\._\-\)\]])"), "Dual Audio"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Multi[\s\.\-_]*Audio)(?:$|[\s\._\-\)\]])"), "Multi Audio"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Hindi[\s\.\-_]*English)(?:$|[\s\._\-\)\]])"), "Hindi + English"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Hindi)(?:$|[\s\._\-\)\]])"), "Hindi"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(English)(?:$|[\s\._\-\)\]])"), "English"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Tamil)(?:$|[\s\._\-\)\]])"), "Tamil"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Telugu)(?:$|[\s\._\-\)\]])"), "Telugu"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Malayalam)(?:$|[\s\._\-\)\]])"), "Malayalam"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Kannada)(?:$|[\s\._\-\)\]])"), "Kannada"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Korean)(?:$|[\s\._\-\)\]])"), "Korean"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(Japanese)(?:$|[\s\._\-\)\]])"), "Japanese"),
        (re.compile(r"(?i)(?:^|[\s\._\-\(\[])(DD[\s\.\-_]*5\.1|5\.1[\s\.\-_]*CH|Dolby|Atmos)(?:$|[\s\._\-\)\]])"), "5.1 Surround"),
    ]

    # Codecs, release groups, and metadata tags
    JUNK_TAGS = [
        r"(?i)\b(BluRay|BRRip|BDRip|WEB[\s\.\-_]*DL|WEBRip|HDTV|HDRip|DVDRip|CAMRip|TeleSync|HDCAM)\b",
        r"(?i)\b(x264|x265|HEVC|AVC|H[\s\.\-_]*264|H[\s\.\-_]*265|10bit|8bit|HDR10\+?|HDR|DV|Dolby\s*Vision)\b",
        r"(?i)\b(AAC2?\.?0?|AC3|EAC3|DTS[\s\.\-_]*HD|DTS|MP3|FLAC|Opus)\b",
        r"(?i)\b(ESub|ESubs|MSub|MSubs|Subs?|English[\s\.\-_]*Sub)\b",
        r"(?i)\b(PSA|GalaxyRG|YIFY|YTS|RARBG|EZTV|TGx|FUM|x0r|PaHe|OlaM|MeGusta|UTR)\b",
        r"(?i)@\w+",       # Channel tags like @Movies_Channel
        r"\[.*?\]",        # Bracketed tags
        r"\{.*?\}",        # Curly tags
    ]

    @classmethod
    def normalize_title(cls, text: str) -> str:
        """Create a clean lowercase normalized version of title for search index."""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def clean_text_separators(cls, text: str) -> str:
        """Replace dots, underscores, dashes with single spaces."""
        text = re.sub(r"[\._\-\+]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def parse(cls, filename: str) -> ParsedMediaInfo:
        raw_name = filename.strip()
        working_str = raw_name

        # 1. Strip file extension
        working_str = re.sub(cls.EXTENSIONS, "", working_str, flags=re.IGNORECASE)

        # 2. Extract Quality early
        quality: Optional[str] = None
        for q_pattern, q_val in cls.QUALITY_PATTERNS:
            if q_pattern.search(working_str):
                quality = q_val
                break

        # 3. Extract Audio
        audio_list = []
        for a_pattern, a_val in cls.AUDIO_PATTERNS:
            if a_pattern.search(working_str) and a_val not in audio_list:
                audio_list.append(a_val)
        audio = " + ".join(audio_list) if audio_list else None

        # 4. Extract Year
        year: Optional[int] = None
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", working_str)
        if year_match:
            year = int(year_match.group(1))

        # 5. Detect Season & Episode
        is_series = False
        season_num: Optional[int] = None
        episode_num: Optional[int] = None
        series_match_span = None

        for pattern in cls.SERIES_PATTERNS:
            match = pattern.search(working_str)
            if match:
                is_series = True
                series_match_span = match.span()
                groupdict = match.groupdict()
                if "season" in groupdict and groupdict["season"]:
                    season_num = int(groupdict["season"])
                if "episode" in groupdict and groupdict["episode"]:
                    episode_num = int(groupdict["episode"])
                break

        if is_series and season_num is None and episode_num is not None:
            season_num = 1

        content_type = "series" if is_series else "movie"

        # 6. Extract clean Title
        title_segment = working_str

        # Remove leading @channel or [bracket] tags first
        title_segment = re.sub(r"^@\w+[\s\._\-]*", "", title_segment)
        title_segment = re.sub(r"^\[.*?\][\s\._\-]*", "", title_segment)

        if series_match_span:
            # Title is before season/episode match
            # Adjust span if we trimmed prefix
            match_in_segment = None
            for pattern in cls.SERIES_PATTERNS:
                m = pattern.search(title_segment)
                if m:
                    match_in_segment = m
                    break
            if match_in_segment:
                prefix = title_segment[:match_in_segment.start()].strip()
                if len(prefix) >= 2:
                    title_segment = prefix
        elif year_match:
            # For movies, title is before the year
            y_in_seg = re.search(r"\b(19\d{2}|20\d{2})\b", title_segment)
            if y_in_seg:
                prefix = title_segment[:y_in_seg.start()].strip()
                if len(prefix) >= 2:
                    title_segment = prefix

        # Strip remaining junk tags
        for tag_regex in cls.JUNK_TAGS:
            title_segment = re.sub(tag_regex, " ", title_segment)

        for q_pattern, _ in cls.QUALITY_PATTERNS:
            title_segment = q_pattern.sub(" ", title_segment)

        # Remove trailing parentheses or brackets like ' (' or ' ['
        title_segment = re.sub(r"[\(\[\{\)\]\}]+", " ", title_segment)

        # Clean separators
        clean_title = cls.clean_text_separators(title_segment)

        if not clean_title or len(clean_title) < 2:
            clean_title = cls.clean_text_separators(re.sub(cls.EXTENSIONS, "", raw_name, flags=re.IGNORECASE))

        clean_title = " ".join(word.capitalize() for word in clean_title.split())
        normalized_title = cls.normalize_title(clean_title)

        return ParsedMediaInfo(
            raw_file_name=raw_name,
            title=clean_title,
            normalized_title=normalized_title,
            content_type=content_type,
            year=year,
            season_number=season_num,
            episode_number=episode_num,
            quality=quality or "Unknown",
            audio=audio
        )
