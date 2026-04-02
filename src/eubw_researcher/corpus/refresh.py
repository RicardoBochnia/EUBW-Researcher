from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from eubw_researcher.models import (
    ArchiveCorpusConfig,
    ArchiveRefreshReport,
    ArchiveRefreshResult,
    RuntimeConfig,
    SourceKind,
    WebAllowlistConfig,
    dataclass_to_dict,
)
from eubw_researcher.web.allowlist import normalize_domain, validate_domain

USER_AGENT = "eubw-researcher-refresh/0.1"


def _load_archive_rows(catalog_path: Path) -> list[dict]:
    with catalog_path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write_archive_rows(catalog_path: Path, rows: list[dict]) -> None:
    catalog_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _blocked_by_keyword(url: str, allowlist: WebAllowlistConfig) -> bool:
    domain = normalize_domain(url)
    policy = allowlist.policy_for_domain(domain)
    if policy is None:
        return False
    lowered = url.lower()
    return any(keyword in lowered for keyword in policy.blocked_url_keywords)


def _matches_allowed_path(url: str, allowlist: WebAllowlistConfig, source_kind: SourceKind) -> bool:
    domain = normalize_domain(url)
    policy = allowlist.policy_for_domain(domain)
    if policy is None:
        return True
    if policy.source_kind != source_kind:
        return False
    path = urlparse(url).path or "/"
    if not policy.allowed_path_prefixes:
        return True
    return any(path.startswith(prefix) for prefix in policy.allowed_path_prefixes)


def _is_refreshable_url(url: Optional[str], allowlist: WebAllowlistConfig, source_kind: SourceKind) -> bool:
    if not url:
        return False
    if not validate_domain(url, allowlist):
        return False
    if _blocked_by_keyword(url, allowlist):
        return False
    return _matches_allowed_path(url, allowlist, source_kind)


def _resolve_refresh_local_path(archive_root: Path, raw_path: str) -> Optional[Path]:
    normalized = raw_path.replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute():
        return None
    parts = list(candidate.parts)
    if parts and parts[0] == "sources":
        parts = parts[1:]
    resolved = (archive_root / Path(*parts)).resolve()
    try:
        resolved.relative_to(archive_root.resolve())
    except ValueError:
        return None
    return resolved


def _relative_archive_path(archive_root: Path, local_path: Path) -> Path:
    return local_path.resolve().relative_to(archive_root.resolve())


def _request_remote_source(
    url: str,
    timeout_seconds: int,
    *,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
) -> tuple[Optional[bytes], Optional[str], Optional[str], Optional[str], bool]:
    headers = {"User-Agent": USER_AGENT}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw_bytes = response.read()
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            remote_etag = response.headers.get("ETag")
            remote_last_modified = response.headers.get("Last-Modified")
            return raw_bytes, content_type, remote_etag, remote_last_modified, False
    except HTTPError as exc:
        if exc.code == 304:
            return None, None, etag, last_modified, True
        raise


def _record_current_result(
    results: list[ArchiveRefreshResult],
    *,
    selection,
    canonical_url: str,
    local_path: Path,
    checked_at: str,
    reason: str,
    local_content_digest: Optional[str],
    remote_etag: Optional[str],
    remote_last_modified: Optional[str],
    content_type: Optional[str] = None,
) -> None:
    results.append(
        ArchiveRefreshResult(
            archive_source_id=selection.archive_source_id,
            source_id=selection.source_id,
            title=selection.title,
            canonical_url=canonical_url,
            local_path=str(local_path),
            checked_at=checked_at,
            status="current",
            reason=reason,
            local_exists=True,
            local_content_digest=local_content_digest,
            remote_content_digest=local_content_digest,
            remote_etag=remote_etag,
            remote_last_modified=remote_last_modified,
            content_type=content_type,
        )
    )


def _stage_candidate(stage_root: Path, archive_root: Path, local_path: Path, raw_bytes: bytes) -> Path:
    stage_path = stage_root / _relative_archive_path(archive_root, local_path)
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    stage_path.write_bytes(raw_bytes)
    return stage_path


def _update_archive_row(
    row: dict,
    *,
    checked_at: str,
    content_digest: str,
    size_bytes: int,
    etag: Optional[str],
    last_modified: Optional[str],
) -> None:
    row["retrieved_at"] = checked_at
    row["sha256"] = content_digest
    row["size_bytes"] = str(size_bytes)
    row["refresh_checked_at"] = checked_at
    if etag is not None:
        row["refresh_etag"] = etag
    if last_modified is not None:
        row["refresh_last_modified"] = last_modified


def refresh_archive_sources(
    config: ArchiveCorpusConfig,
    allowlist: WebAllowlistConfig,
    runtime_config: RuntimeConfig,
    *,
    stage_root: Path,
    config_path: Optional[Path] = None,
    apply_updates: bool = False,
) -> ArchiveRefreshReport:
    archive_rows = _load_archive_rows(config.archive_catalog)
    rows_by_id = {row["source_id"]: row for row in archive_rows}
    results: list[ArchiveRefreshResult] = []
    refreshable_sources = 0

    for selection in config.sources:
        checked_at = datetime.now(timezone.utc).isoformat()
        row = rows_by_id.get(selection.archive_source_id)
        if row is None:
            raise KeyError(
                f"Archive source {selection.archive_source_id} is missing from {config.archive_catalog}."
            )
        canonical_url = row.get("source_url")
        local_path = _resolve_refresh_local_path(config.archive_root, row["local_path"])
        if local_path is None:
            results.append(
                ArchiveRefreshResult(
                    archive_source_id=selection.archive_source_id,
                    source_id=selection.source_id,
                    title=selection.title,
                    canonical_url=canonical_url,
                    local_path=None,
                    checked_at=checked_at,
                    status="skipped_invalid_local_path",
                    reason="Archive catalog local_path is absolute or escapes the archive root.",
                    local_exists=False,
                )
            )
            continue
        local_exists = local_path.exists()
        local_content_digest = _file_digest(local_path) if local_exists else None

        if canonical_url is None:
            results.append(
                ArchiveRefreshResult(
                    archive_source_id=selection.archive_source_id,
                    source_id=selection.source_id,
                    title=selection.title,
                    canonical_url=None,
                    local_path=str(local_path),
                    checked_at=checked_at,
                    status="skipped_missing_canonical_url",
                    reason="No canonical source URL is configured for this archive entry.",
                    local_exists=local_exists,
                    local_content_digest=local_content_digest,
                )
            )
            continue
        if not _is_refreshable_url(canonical_url, allowlist, selection.source_kind):
            results.append(
                ArchiveRefreshResult(
                    archive_source_id=selection.archive_source_id,
                    source_id=selection.source_id,
                    title=selection.title,
                    canonical_url=canonical_url,
                    local_path=str(local_path),
                    checked_at=checked_at,
                    status="skipped_not_allowlisted",
                    reason="Canonical URL is not allowlisted for conservative refresh checks.",
                    local_exists=local_exists,
                    local_content_digest=local_content_digest,
                )
            )
            continue

        refreshable_sources += 1
        try:
            raw_bytes, content_type, remote_etag, remote_last_modified, not_modified = _request_remote_source(
                canonical_url,
                runtime_config.web_timeout_seconds,
                etag=row.get("refresh_etag") if local_exists else None,
                last_modified=row.get("refresh_last_modified") if local_exists else None,
            )
        except Exception as exc:  # pragma: no cover
            results.append(
                ArchiveRefreshResult(
                    archive_source_id=selection.archive_source_id,
                    source_id=selection.source_id,
                    title=selection.title,
                    canonical_url=canonical_url,
                    local_path=str(local_path),
                    checked_at=checked_at,
                    status="fetch_failed",
                    reason=f"Refresh fetch failed: {exc}",
                    local_exists=local_exists,
                    local_content_digest=local_content_digest,
                )
            )
            continue

        if not_modified:
            accepted_digest = row.get("sha256")
            if local_exists and accepted_digest and local_content_digest == accepted_digest:
                if apply_updates:
                    _update_archive_row(
                        row,
                        checked_at=checked_at,
                        content_digest=local_content_digest,
                        size_bytes=local_path.stat().st_size,
                        etag=remote_etag,
                        last_modified=remote_last_modified,
                    )
                _record_current_result(
                    results,
                    selection=selection,
                    canonical_url=canonical_url,
                    local_path=local_path,
                    checked_at=checked_at,
                    reason="Remote source returned not modified and the local archive matches the accepted digest.",
                    local_content_digest=local_content_digest,
                    remote_etag=remote_etag,
                    remote_last_modified=remote_last_modified,
                )
                continue

            try:
                raw_bytes, content_type, remote_etag, remote_last_modified, not_modified = _request_remote_source(
                    canonical_url,
                    runtime_config.web_timeout_seconds,
                )
            except Exception as exc:  # pragma: no cover
                results.append(
                    ArchiveRefreshResult(
                        archive_source_id=selection.archive_source_id,
                        source_id=selection.source_id,
                        title=selection.title,
                        canonical_url=canonical_url,
                        local_path=str(local_path),
                        checked_at=checked_at,
                        status="fetch_failed",
                        reason=(
                            "Conditional refresh reported not modified, but the local archive did not match the "
                            f"accepted digest and fallback fetch failed: {exc}"
                        ),
                        local_exists=local_exists,
                        local_content_digest=local_content_digest,
                    )
                )
                continue

        assert raw_bytes is not None
        remote_content_digest = hashlib.sha256(raw_bytes).hexdigest()
        if local_exists and local_content_digest == remote_content_digest:
            if apply_updates:
                _update_archive_row(
                    row,
                    checked_at=checked_at,
                    content_digest=local_content_digest,
                    size_bytes=local_path.stat().st_size,
                    etag=remote_etag,
                    last_modified=remote_last_modified,
                )
            _record_current_result(
                results,
                selection=selection,
                canonical_url=canonical_url,
                local_path=local_path,
                checked_at=checked_at,
                reason="Remote source digest matches the local archive copy.",
                local_content_digest=local_content_digest,
                remote_etag=remote_etag,
                remote_last_modified=remote_last_modified,
                content_type=content_type,
            )
            continue

        stage_path = _stage_candidate(stage_root, config.archive_root, local_path, raw_bytes)
        applied = False
        status = "staged_update" if local_exists else "staged_missing_local"
        reason = (
            "Remote source differs from the local archive copy and was staged for review."
            if local_exists
            else "Local archive file is missing and a fresh candidate was staged."
        )
        if apply_updates:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(raw_bytes)
            _update_archive_row(
                row,
                checked_at=checked_at,
                content_digest=remote_content_digest,
                size_bytes=len(raw_bytes),
                etag=remote_etag,
                last_modified=remote_last_modified,
            )
            applied = True
            status = "applied_update" if local_exists else "applied_missing_local"
            reason = (
                "Remote source differs from the local archive copy and was applied."
                if local_exists
                else "Local archive file was restored from the configured remote source."
            )

        results.append(
            ArchiveRefreshResult(
                archive_source_id=selection.archive_source_id,
                source_id=selection.source_id,
                title=selection.title,
                canonical_url=canonical_url,
                local_path=str(local_path),
                checked_at=checked_at,
                status=status,
                reason=reason,
                local_exists=local_exists,
                local_content_digest=local_content_digest,
                remote_content_digest=remote_content_digest,
                remote_etag=remote_etag,
                remote_last_modified=remote_last_modified,
                content_type=content_type,
                stage_path=str(stage_path),
                applied=applied,
            )
        )

    if apply_updates:
        _write_archive_rows(config.archive_catalog, archive_rows)

    current_sources = sum(1 for item in results if item.status == "current")
    changed_sources = sum(1 for item in results if "update" in item.status or "missing_local" in item.status)
    staged_sources = sum(1 for item in results if item.status.startswith("staged_"))
    applied_sources = sum(1 for item in results if item.applied)
    skipped_sources = sum(1 for item in results if item.status.startswith("skipped_"))
    failed_sources = sum(1 for item in results if item.status == "fetch_failed")

    return ArchiveRefreshReport(
        config_path=str((config_path or config.archive_catalog).resolve()),
        archive_catalog_path=str(config.archive_catalog.resolve()),
        stage_root=str(stage_root.resolve()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        apply_updates=apply_updates,
        checked_sources=len(results),
        refreshable_sources=refreshable_sources,
        current_sources=current_sources,
        changed_sources=changed_sources,
        staged_sources=staged_sources,
        applied_sources=applied_sources,
        skipped_sources=skipped_sources,
        failed_sources=failed_sources,
        results=results,
    )


def write_archive_refresh_report(report: ArchiveRefreshReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataclass_to_dict(report), indent=2), encoding="utf-8")


def render_archive_refresh_report_markdown(report: ArchiveRefreshReport) -> str:
    lines = [
        "# Real Corpus Refresh Report",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Config: `{report.config_path}`",
        f"- Archive catalog: `{report.archive_catalog_path}`",
        f"- Stage root: `{report.stage_root}`",
        f"- Apply updates: `{str(report.apply_updates).lower()}`",
        f"- Checked / refreshable: `{report.checked_sources}` / `{report.refreshable_sources}`",
        f"- Current / changed: `{report.current_sources}` / `{report.changed_sources}`",
        f"- Staged / applied: `{report.staged_sources}` / `{report.applied_sources}`",
        f"- Skipped / failed: `{report.skipped_sources}` / `{report.failed_sources}`",
        "",
        "## Results",
        "",
    ]
    if not report.results:
        lines.append("- No configured sources were checked.")
        return "\n".join(lines)

    for item in report.results:
        lines.append(
            f"- `{item.source_id}` status=`{item.status}` local_exists=`{str(item.local_exists).lower()}`"
        )
        lines.append(f"  reason: {item.reason}")
        if item.canonical_url:
            lines.append(f"  canonical_url: `{item.canonical_url}`")
        if item.stage_path:
            lines.append(f"  stage_path: `{item.stage_path}`")
        if item.local_content_digest or item.remote_content_digest:
            lines.append(
                "  digests: "
                f"local=`{item.local_content_digest or 'n/a'}` "
                f"remote=`{item.remote_content_digest or 'n/a'}`"
            )
    return "\n".join(lines)
