from __future__ import annotations

from urllib.parse import urlparse

from eubw_researcher.models import WebAllowlistConfig


def normalize_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or parsed.netloc


def validate_domain(url: str, allowlist: WebAllowlistConfig) -> bool:
    return allowlist.is_allowed(normalize_domain(url))
