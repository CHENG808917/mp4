from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class JobOutputs(BaseModel):
    mp4: str
    srt: str


class Job(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    account_id: str = Field(..., description="Account ID, e.g. A, B, C")
    product_id: str = Field(..., description="Product identifier")
    video_filename: str = Field(
        ...,
        description="Safe filename of source MP4 (no path)",
        pattern=r"^[^\\/]+$",
    )
    exact_search_text: str = Field(
        ..., description="Exact seller title text (including symbols and spaces)"
    )
    shop_name: str = Field(..., description="Shop name")
    affiliate_link: str = Field(..., description="Affiliate link")
    status: Literal[
        "queued",
        "subtitling",
        "ready_to_upload",
        "uploaded",
        "failed",
    ] = Field(..., description="Job status")
    created_at: datetime = Field(..., description="ISO datetime")
    updated_at: datetime = Field(..., description="ISO datetime")
    error_reason: Optional[str] = Field(None, description="Error message if failed")
    outputs: Optional[JobOutputs] = Field(
        None, description='Output paths like {"mp4": "...", "srt": "..."}'
    )
