import os
from urllib.parse import urlparse

from browserforge.fingerprints import Screen

PROFILES_DIR = "Profiles"
PROFILE_DIR = "NotBot"
profile_path = os.path.abspath(os.path.join(PROFILES_DIR, PROFILE_DIR))
os.makedirs(profile_path, exist_ok=True)

BROWSER_OPTIONS = {
    "headless": False,
    "os": ["windows"],
    "screen": Screen(max_width=1280, max_height=720),
    "humanize": True,
    "enable_cache": False,
    "persistent_context": True,
    "user_data_dir": profile_path,
    "locale": "en-US",
    # "geoip": True,
}


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
