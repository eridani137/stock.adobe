from urllib.parse import urlparse

from browserforge.fingerprints import Screen

BROWSER_OPTIONS = {
    "headless": False,
    "os": ["windows", "macos", "linux"],
    "screen": Screen(max_width=1280, max_height=720),
    "humanize": True,
    "locale": "en-US"
}


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
