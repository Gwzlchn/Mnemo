"""tests for steps/utils/srt_parser.py"""

from steps.utils.srt_parser import format_timestamp, parse_srt


SAMPLE_SRT = """\
1
00:00:01,000 --> 00:00:03,500
Hello world

2
00:00:05,200 --> 00:00:08,100
This is a test
with two lines

3
00:01:00,000 --> 00:01:05,000
One minute mark
"""


class TestParseSrt:
    def test_basic_parse(self):
        entries = parse_srt(SAMPLE_SRT)
        assert len(entries) == 3
        assert entries[0].index == 1
        assert entries[0].start_sec == 1.0
        assert entries[0].end_sec == 3.5
        assert entries[0].text == "Hello world"

    def test_multiline_text(self):
        entries = parse_srt(SAMPLE_SRT)
        assert entries[1].text == "This is a test\nwith two lines"

    def test_timestamps(self):
        entries = parse_srt(SAMPLE_SRT)
        assert entries[2].start_sec == 60.0
        assert entries[2].end_sec == 65.0

    def test_empty_input(self):
        assert parse_srt("") == []
        assert parse_srt("   \n  \n  ") == []

    def test_malformed_index(self):
        bad = "abc\n00:00:01,000 --> 00:00:02,000\ntext\n"
        assert parse_srt(bad) == []

    def test_malformed_timestamp(self):
        bad = "1\nbad timestamp\ntext\n"
        assert parse_srt(bad) == []

    def test_dot_separator(self):
        srt = "1\n00:00:01.000 --> 00:00:02.500\nhi\n"
        entries = parse_srt(srt)
        assert len(entries) == 1
        assert entries[0].start_sec == 1.0
        assert entries[0].end_sec == 2.5


class TestFormatTimestamp:
    def test_zero(self):
        assert format_timestamp(0) == "[00:00]"

    def test_seconds(self):
        assert format_timestamp(65.3) == "[01:05]"

    def test_large(self):
        assert format_timestamp(3661) == "[61:01]"
