"""
Ableton Live adapter using AbletonOSC.
"""
import socket
import subprocess
import time
from typing import Optional

from pythonosc.osc_message import OscMessage
from pythonosc.udp_client import SimpleUDPClient

from core.base import DAWAdapter, LoadResult, Track


class AbletonAdapter(DAWAdapter):
    def __init__(self, host: str = "127.0.0.1", send_port: int = 11000, recv_port: int = 11001):
        self.host = host
        self.send_port = send_port
        self.recv_port = recv_port
        self._client: Optional[SimpleUDPClient] = None

    def connect(self) -> bool:
        try:
            self._client = SimpleUDPClient(self.host, self.send_port)
            return self.get_tempo() > 0
        except Exception:
            return False

    def _send_and_recv(self, address: str, args: list, timeout: float = 5.0):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self.host, self.recv_port))
        s.settimeout(timeout)
        try:
            self._client.send_message(address, args)
            data, _ = s.recvfrom(4096)
            return list(OscMessage(data))
        finally:
            s.close()

    def _drain_port(self):
        """Drain stale messages from recv port."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self.host, self.recv_port))
        s.settimeout(2)
        self._client.send_message('/live/song/get/tempo', [])
        try:
            while True:
                data, _ = s.recvfrom(4096)
                if OscMessage(data).address == '/live/song/get/tempo':
                    break
        except Exception:
            pass
        finally:
            s.close()

    def create_audio_track(self, index: int, name: Optional[str] = None) -> Track:
        self._client.send_message('/live/song/create_audio_track', [index])
        time.sleep(0.5)
        self._drain_port()
        return Track(index=index, name=name or f"Audio {index + 1}", kind="audio")

    def load_file(self, file_path: str, track_index: int, slot_index: int = 0) -> LoadResult:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self.host, self.recv_port))
        s.settimeout(5)
        try:
            self._client.send_message('/live/browser/load_to_slot', [file_path, track_index, slot_index])
            data, _ = s.recvfrom(4096)
            result = list(OscMessage(data))
            if result and result[0] == 'success':
                return LoadResult(success=True, track=Track(index=track_index, name=file_path, kind="audio"))
            return LoadResult(success=False, error=str(result))
        except Exception as e:
            return LoadResult(success=False, error=str(e))
        finally:
            s.close()

    def copy_to_arrangement(self, track_index: int) -> bool:
        script = '''tell application "Ableton Live 12 Suite" to activate
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
delay 0.2'''
        result = subprocess.run(['osascript', '-e', script], capture_output=True)
        return result.returncode == 0

    def get_tempo(self) -> float:
        try:
            result = self._send_and_recv('/live/song/get/tempo', [], timeout=3)
            return float(result[0]) if result else 0.0
        except Exception:
            return 0.0

    def set_tempo(self, bpm: float) -> bool:
        try:
            self._client.send_message('/live/song/set/tempo', [bpm])
            return True
        except Exception:
            return False
