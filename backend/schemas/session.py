from pydantic import BaseModel
from typing import Optional


class CheckinData(BaseModel):
    emotion: Optional[str] = None
    text: Optional[str] = None


class SessionCreate(BaseModel):
    checkin: Optional[CheckinData] = None


class SessionResponse(BaseModel):
    session_id: str
    status: str = "running"


class SendSummaryRequest(BaseModel):
    email: str
    summary: dict
