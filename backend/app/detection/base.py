from typing import Callable, List, Optional

from pydantic import BaseModel


class DraftEvent(BaseModel):
    event_type: str  # "pick", "ban", "undo", "reset", "map_select", "set_first_pick"
    hero_id: Optional[str] = None
    map_name: Optional[str] = None
    my_team_first: Optional[bool] = None


class BaseDetector:
    def __init__(self):
        self._callbacks: List[Callable[[DraftEvent], None]] = []

    def register_callback(self, callback: Callable[[DraftEvent], None]):
        """Register a handler callback that accepts DraftEvent."""
        self._callbacks.append(callback)

    def trigger_event(self, event: DraftEvent):
        """Trigger callbacks when an event is detected or received."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error executing callback for event {event.event_type}: {e}")

    def start(self):
        """Start the detector (e.g. OpenCV screen grab loop or WebSocket
        listener)"""
        pass

    def stop(self):
        """Stop the detector."""
        pass
