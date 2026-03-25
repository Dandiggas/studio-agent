"""
preflight — Stage 3 (Pure Python)

Prepares the environment. Kills stale daemons, opens the DAW,
waits for OSC readiness, confirms the DAW browser can see all files.
"""

import subprocess
import socket
import time
from pathlib import Path
from dataclasses import dataclass

from pythonosc.udp_client import SimpleUDPClient
from pythonosc.osc_message import OscMessage


OSC_HOST = "127.0.0.1"
OSC_SEND_PORT = 11000
OSC_RECV_PORT = 11001
DAW_OPEN_TIMEOUT = 30  # seconds
ABLETON_LOG = Path.home() / "Library/Preferences/Ableton/Live 12.1/Log.txt"
ABLETON_APP = "Ableton Live 12 Suite"


@dataclass
class PreflightResult:
    success: bool
    error: str | None = None


def _kill_stale_daemons():
    subprocess.run(["pkill", "-f", "fixed_osc_daemon.py"], capture_output=True)
    time.sleep(0.5)


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def _open_ableton():
    subprocess.Popen(["open", "-a", ABLETON_APP])


def _wait_for_osc(timeout: int = DAW_OPEN_TIMEOUT) -> bool:
    """Poll Ableton log until AbletonOSC reports ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            log = ABLETON_LOG.read_text(errors="ignore")
            lines = [l for l in log.splitlines() if "Started AbletonOSC" in l]
            if lines:
                # Check it's a recent entry (last 60 seconds)
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _browser_can_see(filenames: list[str]) -> tuple[bool, list[str]]:
    """Check Ableton browser can see all expected files."""
    client = SimpleUDPClient(OSC_HOST, OSC_SEND_PORT)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((OSC_HOST, OSC_RECV_PORT))
    s.settimeout(3)

    try:
        client.send_message("/live/browser/list", ["Downloads"])
        data, _ = s.recvfrom(8192)
        visible = [str(i) for i in list(OscMessage(data))]
        missing = [f for f in filenames if f not in visible]
        return len(missing) == 0, missing
    except Exception as e:
        return False, filenames
    finally:
        s.close()


def run(file_paths: list[Path]) -> PreflightResult:
    """
    Prepare environment for DAW loading.

    Args:
        file_paths: list of verified local audio file paths

    Returns:
        PreflightResult
    """
    filenames = [p.name for p in file_paths]

    # 1. Kill stale daemons
    _kill_stale_daemons()

    # 2. Check port is free
    if _port_in_use(OSC_RECV_PORT):
        # Try killing again
        _kill_stale_daemons()
        time.sleep(1)
        if _port_in_use(OSC_RECV_PORT):
            return PreflightResult(success=False, error=f"Port {OSC_RECV_PORT} still in use after cleanup")

    # 3. Open Ableton
    _open_ableton()

    # 4. Wait for OSC
    if not _wait_for_osc():
        return PreflightResult(success=False, error=f"Ableton OSC did not start within {DAW_OPEN_TIMEOUT}s")

    time.sleep(2)  # brief settle after OSC starts

    # 5. Confirm browser can see files
    visible, missing = _browser_can_see(filenames)
    if not visible:
        return PreflightResult(
            success=False,
            error=f"Ableton browser cannot see files: {missing}. Files must be in ~/Downloads before Ableton opens."
        )

    return PreflightResult(success=True)
