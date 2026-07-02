"""URL 추출 테스트."""

from parser.url_extractor import UrlExtractor


def test_extract_multiple_urls() -> None:
    extractor = UrlExtractor()
    text = "visit https://instagram.com/a and www.youtube.com/x"
    urls = extractor.extract(text)
    assert "https://instagram.com/a" in urls
    assert any("youtube.com" in u for u in urls)
