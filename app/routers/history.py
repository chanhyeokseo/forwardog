from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from app.models import HistoryEntry, HistoryEntryType
from app.services.history import history_service

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/", response_model=list[HistoryEntry])
async def get_history(
    limit: Optional[int] = None,
    entry_type: Optional[HistoryEntryType] = None
):
    """Get submission history"""
    if entry_type:
        return history_service.get_by_type(entry_type, limit)
    return history_service.get_all(limit)


@router.get("/{entry_id}", response_model=HistoryEntry)
async def get_history_entry(entry_id: str):
    """Get a specific history entry"""
    entry = history_service.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/")
async def clear_history():
    """Clear all history"""
    history_service.clear()
    return {"message": "History cleared"}


@router.get("/export/json", response_class=PlainTextResponse)
async def export_history():
    """Export history as JSON"""
    return PlainTextResponse(
        content=history_service.export_json(),
        media_type="application/json"
    )

