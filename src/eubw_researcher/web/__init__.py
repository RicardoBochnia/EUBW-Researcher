"""Allowlist-only web helpers."""

from .allowlist import normalize_domain, validate_domain
from .fetch import fetch_and_normalize_official_sources

__all__ = ["fetch_and_normalize_official_sources", "normalize_domain", "validate_domain"]
