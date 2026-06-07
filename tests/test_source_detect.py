"""tests for shared/source_detect.py"""

from shared.source_detect import detect_source, extract_arxiv_id, extract_bilibili_bvid


class TestDetectSource:
    def test_bilibili_full_url(self):
        assert detect_source("https://www.bilibili.com/video/BV1xx411c7mD") == "bilibili"

    def test_bilibili_bvid_only(self):
        assert detect_source("BV1xx411c7mD") == "bilibili"

    def test_bilibili_short_url(self):
        assert detect_source("https://b23.tv/abc123") == "bilibili"

    def test_youtube_full(self):
        assert detect_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"

    def test_youtube_short(self):
        assert detect_source("https://youtu.be/dQw4w9WgXcQ") == "youtube"

    def test_arxiv(self):
        assert detect_source("https://arxiv.org/abs/2301.00001") == "arxiv"

    def test_arxiv_pdf(self):
        assert detect_source("https://arxiv.org/pdf/2301.00001") == "arxiv"

    def test_empty_string(self):
        assert detect_source("") == "other"

    def test_http_article(self):
        assert detect_source("https://example.com/post/intro-to-rust") == "http_article"

    def test_http_article_no_path(self):
        assert detect_source("http://blog.example.org") == "http_article"

    def test_podcast_mp3(self):
        assert detect_source("https://cdn.example.com/ep/42.mp3") == "podcast"

    def test_podcast_m4a_with_query(self):
        assert detect_source("https://cdn.example.com/ep/42.m4a?token=abc") == "podcast"

    def test_podcast_wav(self):
        assert detect_source("https://cdn.example.com/clip.wav") == "podcast"

    def test_non_http_unknown_stays_other(self):
        assert detect_source("ftp://example.com/file") == "other"

    def test_bare_identifier_stays_other(self):
        assert detect_source("just-some-text") == "other"

    def test_known_sources_unchanged(self):
        # 新判定不得改动既有来源识别。
        assert detect_source("https://www.bilibili.com/video/BV1xx411c7mD") == "bilibili"
        assert detect_source("https://youtu.be/dQw4w9WgXcQ") == "youtube"
        assert detect_source("https://arxiv.org/abs/2301.00001") == "arxiv"


class TestExtractBvid:
    def test_from_url(self):
        assert extract_bilibili_bvid("https://www.bilibili.com/video/BV1xx411c7mD") == "BV1xx411c7mD"

    def test_bare_bvid(self):
        assert extract_bilibili_bvid("BV1xx411c7mD") == "BV1xx411c7mD"

    def test_no_match(self):
        assert extract_bilibili_bvid("https://example.com") is None


class TestExtractArxivId:
    def test_abs_url(self):
        assert extract_arxiv_id("https://arxiv.org/abs/2301.00001") == "2301.00001"

    def test_pdf_url(self):
        assert extract_arxiv_id("https://arxiv.org/pdf/2301.00001") == "2301.00001"

    def test_no_match(self):
        assert extract_arxiv_id("https://example.com") is None
