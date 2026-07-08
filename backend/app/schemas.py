from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    meeting_id: int
    status: str


class ProcessResponse(BaseModel):
    meeting_id: int
    status: str
    report: str | None = None


class ReportUpdateRequest(BaseModel):
    report_markdown: str


class MeetingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    meeting_date: str
    participants: str
    project_name: str | None
    meeting_type: str
    report_type: str = "meeting"
    custom_prompt: str | None = None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MeetingDetail(MeetingListItem):
    image_file_paths: list[str] | None = None
    image_context: str | None = None
    transcript: str | None = None
    summary_json: dict[str, Any] | None = None
    report_markdown: str | None = None
