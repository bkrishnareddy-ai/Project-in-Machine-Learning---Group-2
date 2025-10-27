# src/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    due_at: Optional[str] = Field(None, description="ISO 8601 datetime string (UTC)")
    status: Optional[str] = Field("pending", description="Reminder status: pending/done/canceled")

class ReminderItem(BaseModel):
    id: int
    user_id: int
    title: str
    due_at: Optional[str]
    status: Literal["pending", "done", "canceled"]
    created_at: str
    updated_at: str

class ReminderListResponse(BaseModel):
    items: List[ReminderItem]
    total: int
