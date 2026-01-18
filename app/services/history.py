import json
from datetime import datetime
from typing import Optional
from collections import deque
import uuid
from app.config import settings
from app.models import HistoryEntry, HistoryEntryType, SubmitResponse


class HistoryService:
    def __init__(self, max_items: int = None):
        self.max_items = max_items or settings.max_history_items
        self._history: deque[HistoryEntry] = deque(maxlen=self.max_items)
    
    def add(
        self,
        entry_type: HistoryEntryType,
        request: dict,
        response: SubmitResponse
    ) -> HistoryEntry:
        entry = HistoryEntry(
            id=str(uuid.uuid4())[:8],
            type=entry_type,
            timestamp=datetime.utcnow(),
            request=request,
            response=response
        )
        self._history.appendleft(entry)
        return entry
    
    def get_all(self, limit: Optional[int] = None) -> list[HistoryEntry]:
        entries = list(self._history)
        if limit:
            return entries[:limit]
        return entries
    
    def get_by_type(self, entry_type: HistoryEntryType, limit: Optional[int] = None) -> list[HistoryEntry]:
        entries = [e for e in self._history if e.type == entry_type]
        if limit:
            return entries[:limit]
        return entries
    
    def get_by_id(self, entry_id: str) -> Optional[HistoryEntry]:
        for entry in self._history:
            if entry.id == entry_id:
                return entry
        return None
    
    def clear(self):
        self._history.clear()
    
    def export_json(self) -> str:
        return json.dumps(
            [entry.model_dump(mode='json') for entry in self._history],
            indent=2,
            default=str
        )


history_service = HistoryService()
