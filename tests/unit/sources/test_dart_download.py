"""Unit tests for download_corp_code_zip — error branches with mocked HTTP."""

import io
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pytest

from k_fingraph.errors import DartAPIError
from k_fingraph.sources.dart import download_corp_code_zip


def _patch_httpx_get(monkeypatch: pytest.MonkeyPatch, response: httpx.Response) -> None:
    """Replace httpx.get used by sources.dart with one that returns a fixed Response."""

    def fake_get(url: str, *, params: Any = None, timeout: Any = None) -> httpx.Response:
        return response

    monkeypatch.setattr("k_fingraph.sources.dart.httpx.get", fake_get)


@pytest.mark.unit
def test_html_error_page_raises_dart_api_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # DART redirects to an HTML error page (200 OK) when the key is rejected
    # or the daily quota is exhausted — body has no ZIP magic bytes.
    _patch_httpx_get(
        monkeypatch,
        httpx.Response(200, content=b"<html><body>error</body></html>"),
    )

    with pytest.raises(DartAPIError, match="not a ZIP"):
        download_corp_code_zip("dummy-key", tmp_path)


@pytest.mark.unit
def test_http_500_raises_dart_api_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_httpx_get(
        monkeypatch,
        httpx.Response(500, content=b"upstream blew up"),
    )

    with pytest.raises(DartAPIError, match="HTTP 500"):
        download_corp_code_zip("dummy-key", tmp_path)


@pytest.mark.unit
def test_zip_without_xml_raises_dart_api_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Valid ZIP but contains no XML — should be rejected rather than silently
    # returning a non-XML path.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("README.txt", "no xml here")
    _patch_httpx_get(monkeypatch, httpx.Response(200, content=buf.getvalue()))

    with pytest.raises(DartAPIError, match="no XML"):
        download_corp_code_zip("dummy-key", tmp_path)


@pytest.mark.unit
def test_corrupt_zip_raises_dart_api_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # PK magic bytes present so we get past the not-a-ZIP check, but the
    # archive itself is unreadable — zipfile raises BadZipFile, which we
    # convert to DartAPIError.
    _patch_httpx_get(monkeypatch, httpx.Response(200, content=b"PK\x03\x04garbage-bytes"))

    with pytest.raises(DartAPIError, match="corrupt ZIP"):
        download_corp_code_zip("dummy-key", tmp_path)
