from app.detection.base import BaseDetector, DraftEvent


class ManualDetector(BaseDetector):
    """Detector for manual inputs.

    Events are injected directly via HTTP POST requests or WebSocket
    messages from the UI.
    """

    def send_event(self, event: DraftEvent):
        self.trigger_event(event)
