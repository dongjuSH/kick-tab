from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.models.feedback import FEEDBACK_BODY_MAX, FEEDBACK_PAGE_PATH_MAX
from app.schemas.common import ApiModel

FeedbackType = Literal["bug", "suggestion", "other"]


class FeedbackCreate(ApiModel):
    # Required, 1~1,000 characters after trimming; whitespace-only is rejected (FEED-002).
    body: str = Field(max_length=FEEDBACK_BODY_MAX * 2)
    # Required by user decision (2026-10-31), replacing "선택" in FEED-002/PRD 21.
    # The DB column stays nullable for rows saved before this change.
    type: FeedbackType
    # Current screen path only (no query string), used to group feedback by page.
    page_path: str | None = Field(default=None, max_length=FEEDBACK_PAGE_PATH_MAX)

    @field_validator("body")
    @classmethod
    def body_has_content(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("공백 외 내용을 입력해 주세요.")
        if len(trimmed) > FEEDBACK_BODY_MAX:
            raise ValueError(f"최대 {FEEDBACK_BODY_MAX:,}자까지 입력할 수 있습니다.")
        return trimmed

    @field_validator("page_path")
    @classmethod
    def page_path_is_internal(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("내부 경로만 기록할 수 있습니다.")
        return value.split("?", 1)[0].split("#", 1)[0]


class FeedbackReceipt(ApiModel):
    id: int
    created_at: datetime
