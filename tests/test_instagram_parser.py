"""Instagram 파서 테스트."""

from parser.instagram import InstagramNormalizer
from parser.url_extractor import UrlExtractor


class TestInstagramNormalizer:
    def setup_method(self) -> None:
        self.normalizer = InstagramNormalizer()
        self.extractor = UrlExtractor()

    def test_profile_urls(self) -> None:
        cases = [
            ("https://instagram.com/abc", "abc"),
            ("https://www.instagram.com/abc/", "abc"),
            ("https://www.instagram.com/abc?igsh=xxxxx", "abc"),
            ("http://instagram.com/MyUser.Name", "myuser.name"),
        ]
        for url, expected in cases:
            result = self.normalizer.parse_url(url)
            assert result is not None
            assert result.username == expected

    def test_exclude_non_profile(self) -> None:
        urls = [
            "https://www.instagram.com/p/ABC123/",
            "https://www.instagram.com/reel/xyz/",
            "https://youtube.com/watch?v=1",
            "https://naver.com",
        ]
        for url in urls:
            assert self.normalizer.parse_url(url) is None

    def test_parse_text_deduplicates(self) -> None:
        text = "follow https://instagram.com/abc and https://www.instagram.com/abc/"
        urls = self.extractor.extract(text)
        results = self.normalizer.parse_text(text, urls)
        assert len(results) == 1
        assert results[0].username == "abc"

    def test_bare_instagram_domain(self) -> None:
        text = "check instagram.com/hello_world"
        urls = self.extractor.extract(text)
        results = self.normalizer.parse_text(text, urls)
        assert len(results) == 1
        assert results[0].username == "hello_world"
