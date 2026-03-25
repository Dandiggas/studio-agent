"""
Studio Agent — main pipeline entry point.

Usage:
    python -m pipeline.run "load the stems from my email"
"""

import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from pipeline import email_parser, downloader, preflight, loader, verifier


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_credentials() -> Credentials:
    """Load or refresh Google OAuth credentials."""
    token_path = Path.home() / ".studio-agent" / "token.json"
    creds_path = Path.home() / ".studio-agent" / "credentials.json"

    if token_path.exists():
        return Credentials.from_authorized_user_file(str(token_path), SCOPES)

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds


def run(instruction: str):
    print(f"Studio Agent starting: '{instruction}'\n")

    # Stage 1 — parse email
    print("→ Parsing email...")
    creds = get_credentials()
    email_result = email_parser.run(instruction, creds)
    if not email_result.success:
        print(f"✗ Email parser failed: {email_result.error}")
        return

    print(f"✓ Found {len(email_result.stems)} stems")

    # Stage 2 — download
    print("→ Downloading stems...")
    download_result = downloader.run(email_result.stems, creds)
    if not download_result.success:
        print(f"✗ All downloads failed")
        return

    if download_result.failed:
        print(f"⚠ {len(download_result.failed)} stems failed to download:")
        for f in download_result.failed:
            print(f"  - {f.original_stem.filename}: {f.error}")

    file_paths = [f.local_path for f in download_result.files]
    print(f"✓ Downloaded {len(file_paths)} stems")

    # Stage 3 — preflight
    print("→ Running preflight checks...")
    preflight_result = preflight.run(file_paths)
    if not preflight_result.success:
        print(f"✗ Preflight failed: {preflight_result.error}")
        return

    print("✓ Ableton ready")

    # Stage 4 — load
    print("→ Loading stems into Ableton...")
    loader_result = loader.run(file_paths)

    if loader_result.failed:
        print(f"⚠ {len(loader_result.failed)} tracks failed to load:")
        for f in loader_result.failed:
            print(f"  - {f.filename}: {f.error}")

    # Stage 5 — verify
    expected = [p.name for p in file_paths]
    verify_result = verifier.run(expected, loader_result.tracks)

    print(f"\n{'✓' if verify_result.success else '⚠'} {verify_result.message}")


if __name__ == "__main__":
    instruction = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "load the stems from my email"
    run(instruction)
