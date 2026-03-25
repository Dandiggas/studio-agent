"""
downloader — Stage 2 (Pure Python)

Downloads all stems in parallel. Validates each file is genuine audio.
Normalises filenames. Retries up to 3x per file.
"""

import asyncio
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from pipeline.email_parser import Stem


DOWNLOAD_DIR = Path.home() / "Downloads"
MAX_RETRIES = 3
AUDIO_MAGIC_BYTES = [
    b"ID3",           # MP3
    b"\xff\xfb",      # MP3
    b"\xff\xf3",      # MP3
    b"\xff\xf2",      # MP3
    b"FORM",          # AIFF
    b"RIFF",          # WAV
    b"fLaC",          # FLAC
    b"OggS",          # OGG
]


@dataclass
class DownloadedFile:
    original_stem: Stem
    local_path: Path
    success: bool
    error: str | None = None


@dataclass
class DownloaderResult:
    success: bool
    files: list[DownloadedFile]
    failed: list[DownloadedFile]


def _normalise_filename(name: str) -> str:
    """Remove spaces, brackets, special chars from filename."""
    stem = Path(name).stem
    suffix = Path(name).suffix or ".mp3"
    clean = re.sub(r"[^\w\-]", "_", stem)
    clean = re.sub(r"_+", "_", clean).strip("_")
    return f"{clean}{suffix}"


def _is_valid_audio(path: Path) -> bool:
    """Check file magic bytes to confirm it's real audio."""
    try:
        with open(path, "rb") as f:
            header = f.read(16)
        return any(header.startswith(magic) for magic in AUDIO_MAGIC_BYTES)
    except Exception:
        return False


def _download_attachment(stem: Stem, creds: Credentials) -> Path | None:
    """Download a direct Gmail attachment."""
    service = build("gmail", "v1", credentials=creds)
    attachment = service.users().messages().attachments().get(
        userId="me",
        messageId=stem.message_id,
        id=stem.attachment_id
    ).execute()

    import base64
    data = base64.urlsafe_b64decode(attachment["data"] + "==")
    filename = _normalise_filename(stem.filename)
    path = DOWNLOAD_DIR / filename
    path.write_bytes(data)
    return path


def _download_drive(stem: Stem, creds: Credentials) -> Path | None:
    """Download from Google Drive."""
    # Extract file ID from Drive URL
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", stem.url or "")
    if not match:
        return None

    file_id = match.group(1)
    drive_service = build("drive", "v3", credentials=creds)
    request = drive_service.files().get_media(fileId=file_id)

    filename = _normalise_filename(stem.filename or f"{file_id}.mp3")
    path = DOWNLOAD_DIR / filename
    with open(path, "wb") as f:
        f.write(request.execute())
    return path


def _download_url(stem: Stem) -> Path | None:
    """Download from a direct URL (WeTransfer, Dropbox, etc.)."""
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        response = client.get(stem.url)
        response.raise_for_status()

        filename = _normalise_filename(stem.filename or "stem.mp3")
        path = DOWNLOAD_DIR / filename
        path.write_bytes(response.content)
        return path


def _download_one(stem: Stem, creds: Credentials) -> DownloadedFile:
    """Download a single stem with retries."""
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            path = None

            if stem.source == "attachment":
                path = _download_attachment(stem, creds)
            elif stem.source == "drive":
                path = _download_drive(stem, creds)
            elif stem.source in ("wetransfer", "dropbox", "unknown"):
                path = _download_url(stem)

            if path and _is_valid_audio(path):
                return DownloadedFile(original_stem=stem, local_path=path, success=True)
            elif path:
                path.unlink(missing_ok=True)
                last_error = "Downloaded file is not valid audio"

        except Exception as e:
            last_error = str(e)

    return DownloadedFile(
        original_stem=stem,
        local_path=Path(""),
        success=False,
        error=last_error
    )


def run(stems: list[Stem], creds: Credentials) -> DownloaderResult:
    """
    Download all stems. Returns successful and failed downloads.

    Args:
        stems: list of Stem objects from email_parser
        creds: Google OAuth credentials

    Returns:
        DownloaderResult with files and failed lists
    """
    results = [_download_one(stem, creds) for stem in stems]

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    return DownloaderResult(
        success=len(successful) > 0,
        files=successful,
        failed=failed
    )
