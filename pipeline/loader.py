"""
loader — Stage 4 (Pure Python)

Loads each stem into the DAW one at a time.
Verifies each track before moving to the next.
"""

import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from pythonosc.udp_client import SimpleUDPClient
from pythonosc.osc_message import OscMessage


OSC_HOST = "127.0.0.1"
OSC_SEND_PORT = 11000
OSC_RECV_PORT = 11001

APPLESCRIPT = """tell application "Ableton Live 12 Suite" to activate
delay 0.2
tell application "System Events" to tell process "Live" to keystroke "c" using command down
delay 0.15
tell application "System Events" to tell process "Live" to key code 48
delay 0.2
tell application "System Events" to tell process "Live" to key code 115
delay 0.1
tell application "System Events" to tell process "Live" to keystroke "v" using command down
delay 0.2
tell application "System Events" to tell process "Live" to key code 48
delay 0.2"""


@dataclass
class TrackResult:
    index: int
    filename: str
    success: bool
    error: str | None = None


@dataclass
class LoaderResult:
    success: bool
    tracks: list[TrackResult]
    failed: list[TrackResult]


def _drain_port(client: SimpleUDPClient):
    """Send a tempo ping and drain stale OSC messages."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((OSC_HOST, OSC_RECV_PORT))
    s.settimeout(2)
    client.send_message("/live/song/get/tempo", [])
    try:
        while True:
            data, _ = s.recvfrom(4096)
            if OscMessage(data).address == "/live/song/get/tempo":
                break
    except Exception:
        pass
    finally:
        s.close()


def _get_arrangement_clip_count(client: SimpleUDPClient) -> int:
    """Query Ableton for current arrangement clip count."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((OSC_HOST, OSC_RECV_PORT))
    s.settimeout(3)
    try:
        client.send_message("/live/song/get/num_tracks", [])
        data, _ = s.recvfrom(4096)
        return int(list(OscMessage(data))[0])
    except Exception:
        return -1
    finally:
        s.close()


def _copy_to_arrangement() -> bool:
    """Copy session clip to arrangement via AppleScript."""
    result = subprocess.run(["osascript", "-e", APPLESCRIPT], capture_output=True)
    return result.returncode == 0


def _load_track(client: SimpleUDPClient, filename: str, index: int, first_track: bool = False) -> TrackResult:
    """Load a single stem to a track. Retries once on failure."""
    browser_path = f"Downloads/{filename}"

    for attempt in range(2):
        try:
            # Create audio track
            client.send_message("/live/song/create_audio_track", [index])
            time.sleep(0.5)

            # Drain port
            _drain_port(client)

            # Load to session slot
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind((OSC_HOST, OSC_RECV_PORT))
            s.settimeout(5)
            client.send_message("/live/browser/load_to_slot", [browser_path, index, 0])

            try:
                data, _ = s.recvfrom(4096)
                result = list(OscMessage(data))
                if not result or result[0] != "success":
                    raise ValueError(f"load_to_slot returned: {result}")
            finally:
                s.close()

            # Extra settle time for first track
            time.sleep(1.0 if (first_track or attempt > 0) else 0.5)

            # Copy to arrangement
            _copy_to_arrangement()
            time.sleep(0.5)

            return TrackResult(index=index, filename=filename, success=True)

        except Exception as e:
            if attempt == 0:
                time.sleep(1)  # wait before retry
                continue
            return TrackResult(index=index, filename=filename, success=False, error=str(e))

    return TrackResult(index=index, filename=filename, success=False, error="Max retries exceeded")


def run(file_paths: list[Path]) -> LoaderResult:
    """
    Load all stems into Ableton.

    Args:
        file_paths: verified local audio file paths

    Returns:
        LoaderResult with per-track success/fail
    """
    client = SimpleUDPClient(OSC_HOST, OSC_SEND_PORT)
    results = []

    for idx, path in enumerate(file_paths):
        result = _load_track(client, path.name, idx, first_track=(idx == 0))
        results.append(result)

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    return LoaderResult(
        success=len(failed) == 0,
        tracks=successful,
        failed=failed
    )
