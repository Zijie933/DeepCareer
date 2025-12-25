"""
简历相关的 Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ResumeUploadResponse(BaseModel):
    """简历上传响应"""
    success: bool
    resume_id: int
    file_name: str
    message: str


class ResumeParseResponse(BaseModel):
    """简历解析响应"""
    success: bool
    resume_id: int
    full_text: str
    parsed_data: Optional[Dict[str, Any]] = None
    analysis_result: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    message: str


class ResumeDetailResponse(BaseModel):
    """简历详情响应"""
    id: int
    file_name: str
    file_type: str
    full_text: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    analysis_result: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
