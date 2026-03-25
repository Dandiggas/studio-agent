"""
daw-mcp: DAW-agnostic AI agent interface
Base adapter class — all DAW adapters implement this interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class Track:
    index: int
    name: str
    kind: str  # "audio" | "midi" | "group"


@dataclass
class LoadResult:
    success: bool
    track: Optional[Track] = None
    error: Optional[str] = None


class DAWAdapter(ABC):
    """Base interface for all DAW adapters."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the DAW."""
        pass

    @abstractmethod
    def create_audio_track(self, index: int, name: Optional[str] = None) -> Track:
        """Create a new audio track at the given index."""
        pass

    @abstractmethod
    def load_file(self, file_path: str, track_index: int, slot_index: int = 0) -> LoadResult:
        """Load an audio file into a track slot."""
        pass

    @abstractmethod
    def copy_to_arrangement(self, track_index: int) -> bool:
        """Copy a session clip to the arrangement view."""
        pass

    @abstractmethod
    def get_tempo(self) -> float:
        """Get the current BPM."""
        pass

    @abstractmethod
    def set_tempo(self, bpm: float) -> bool:
        """Set the tempo."""
        pass
