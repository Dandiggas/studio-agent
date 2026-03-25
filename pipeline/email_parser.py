"""
email_parser — Stage 1 (LLM)

Parses a natural language instruction, finds the relevant email,
and returns a structured list of stems with their source types.
"""

import base64
import re
from dataclasses import dataclass
from typing import Literal

from anthropic import Anthropic
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


StemSource = Literal["attachment", "drive", "wetransfer", "dropbox", "unknown"]


@dataclass
class Stem:
    filename: str
    source: StemSource
    attachment_id: str | None = None   # for direct attachments
    url: str | None = None             # for Drive / WeTransfer / Dropbox
    message_id: str | None = None


@dataclass
class EmailParserResult:
    success: bool
    stems: list[Stem]
    message_id: str | None = None
    error: str | None = None


def _classify_url(url: str) -> StemSource:
    if "drive.google.com" in url:
        return "drive"
    if "wetransfer.com" in url:
        return "wetransfer"
    if "dropbox.com" in url:
        return "dropbox"
    return "unknown"


def _extract_links(text: str) -> list[str]:
    return re.findall(r'https?://[^\s<>"]+', text)


def _decode_body(data: str) -> str:
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")


def _parse_message(message: dict) -> list[Stem]:
    """Extract stems from a Gmail message payload."""
    stems = []
    message_id = message["id"]
    payload = message["payload"]

    # Direct attachments
    parts = payload.get("parts", [])
    for part in parts:
        mime = part.get("mimeType", "")
        filename = part.get("filename", "")
        body = part.get("body", {})
        attachment_id = body.get("attachmentId")

        if mime.startswith("audio/") or (filename.endswith(".mp3") or filename.endswith(".wav") or filename.endswith(".aiff")):
            if attachment_id:
                stems.append(Stem(
                    filename=filename,
                    source="attachment",
                    attachment_id=attachment_id,
                    message_id=message_id
                ))

    # Links in body
    for part in parts:
        if part.get("mimeType") in ("text/plain", "text/html"):
            data = part.get("body", {}).get("data", "")
            if data:
                text = _decode_body(data)
                links = _extract_links(text)
                for link in links:
                    source = _classify_url(link)
                    if source != "unknown":
                        # Try to extract filename from URL or use placeholder
                        filename = link.split("/")[-1].split("?")[0] or "stem.mp3"
                        stems.append(Stem(
                            filename=filename,
                            source=source,
                            url=link,
                            message_id=message_id
                        ))

    return stems


def run(instruction: str, creds: Credentials) -> EmailParserResult:
    """
    Parse a natural language instruction and find stems in Gmail.

    Args:
        instruction: e.g. "load the stems from my email"
        creds: Google OAuth credentials

    Returns:
        EmailParserResult with list of stems
    """
    client = Anthropic()
    service = build("gmail", "v1", credentials=creds)

    # Use LLM to extract search intent from instruction
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=256,
        system="You are a Gmail search query generator. Given a natural language instruction about finding music stems or audio files in email, output ONLY a Gmail search query string. Nothing else.",
        messages=[{"role": "user", "content": instruction}]
    )
    query = response.content[0].text.strip()

    # Search Gmail
    results = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
    messages = results.get("messages", [])

    if not messages:
        return EmailParserResult(success=False, stems=[], error=f"No emails found for query: {query}")

    # Check most recent matching messages for audio
    for msg_ref in messages:
        message = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
        stems = _parse_message(message)
        if stems:
            return EmailParserResult(
                success=True,
                stems=stems,
                message_id=msg_ref["id"]
            )

    return EmailParserResult(success=False, stems=[], error="Emails found but no audio files detected")
