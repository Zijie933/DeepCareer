"""
反馈相关的 Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class FeedbackRequest(BaseModel):
    """反馈请求"""
    resume_id: int
    job_id: int
    search_history_id: Optional[int] = None
    feedback_type: str = Field(..., description="like/dislike/apply/view/share")
    rating: Optional[float] = Field(None, ge=1, le=5, description="评分（1-5）")
    comment: Optional[str] = None
    feedback_details: Optional[Dict[str, Any]] = None


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    feedback_id: int
    message: str
