"""Capture ordered user-facing events for an individual processing run."""
from copy import deepcopy
from datetime import datetime, timezone


class ProcessingHistory:
    def __init__(self, callback):
        self.callback = callback
        self.events = []

    def __call__(self, event):
        if event.get('type') not in ('complete', 'error') and (event.get('title') or event.get('message')):
            row = deepcopy({key: value for key, value in event.items() if key not in ('type', 'result')})
            row['title'] = row.get('title') or row.get('message')
            row.setdefault('timestamp', datetime.now(timezone.utc).isoformat())
            self.events.append(row)
        return self.callback(event)

    def snapshot(self, fallback=None):
        return deepcopy(self.events or fallback or [])
