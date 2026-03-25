"""
Reaper adapter — coming soon.
"""
from typing import Optional
from core.base import DAWAdapter, LoadResult, Track


class ReaperAdapter(DAWAdapter):
    """Reaper adapter via OSC + ReaScript. Not yet implemented."""

    def connect(self) -> bool:
        raise NotImplementedError("Reaper adapter coming soon")

    def create_audio_track(self, index: int, name: Optional[str] = None) -> Track:
        raise NotImplementedError

    def load_file(self, file_path: str, track_index: int, slot_index: int = 0) -> LoadResult:
        raise NotImplementedError

    def copy_to_arrangement(self, track_index: int) -> bool:
        raise NotImplementedError

    def get_tempo(self) -> float:
        raise NotImplementedError

    def set_tempo(self, bpm: float) -> bool:
        raise NotImplementedError
