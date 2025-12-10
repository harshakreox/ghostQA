"""
Action Recorder Module

Records human interactions with web applications to learn
test patterns and element selectors from demonstrations.
"""

from .action_recorder import ActionRecorder, RecordedAction, RecordingSession

__all__ = [
    "ActionRecorder",
    "RecordedAction",
    "RecordingSession"
]
