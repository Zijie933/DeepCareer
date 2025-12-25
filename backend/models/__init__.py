"""
Models Package
"""
from backend.models.resume_v2 import ResumeV2 as Resume  # 使用V2版本
from backend.models.job_v2 import JobV2 as Job  # 使用V2版本
from backend.models.feedback import UserFeedback
from backend.models.search_history import SearchHistory

__all__ = [
    "Resume",
    "Job",
    "UserFeedback",
    "SearchHistory",
]
