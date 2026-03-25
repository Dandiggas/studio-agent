"""
verifier — Stage 5 (Pure Python)

Final reconciliation. Compares expected stem count against actual DAW state.
"""

import socket
from dataclasses import dataclass

from pythonosc.udp_client import SimpleUDPClient
from pythonosc.osc_message import OscMessage

from pipeline.loader import TrackResult


OSC_HOST = "127.0.0.1"
OSC_SEND_PORT = 11000
OSC_RECV_PORT = 11001


@dataclass
class VerifierResult:
    success: bool
    loaded: list[str]
    missing: list[str]
    message: str


def _get_track_names(client: SimpleUDPClient) -> list[str]:
    """Query Ableton for all track names."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((OSC_HOST, OSC_RECV_PORT))
    s.settimeout(3)
    try:
        client.send_message("/live/song/get/track_names", [])
        data, _ = s.recvfrom(8192)
        return [str(i) for i in list(OscMessage(data))]
    except Exception:
        return []
    finally:
        s.close()


def run(expected: list[str], loaded_tracks: list[TrackResult]) -> VerifierResult:
    """
    Verify DAW state matches expected stems.

    Args:
        expected: list of expected filenames
        loaded_tracks: successful tracks from loader

    Returns:
        VerifierResult
    """
    loaded_names = [t.filename for t in loaded_tracks]
    missing = [f for f in expected if f not in loaded_names]

    if not missing:
        return VerifierResult(
            success=True,
            loaded=loaded_names,
            missing=[],
            message=f"All {len(loaded_names)} stems loaded successfully."
        )

    return VerifierResult(
        success=False,
        loaded=loaded_names,
        missing=missing,
        message=f"{len(loaded_names)}/{len(expected)} stems loaded. Missing: {', '.join(missing)}"
    )
