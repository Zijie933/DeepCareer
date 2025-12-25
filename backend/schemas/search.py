"""
搜索相关的 Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class SearchPreferences(BaseModel):
    """搜索偏好设置"""
    locations: List[str] = Field(default=[], description="期望工作城市")
    industries: List[str] = Field(default=[], description="期望行业")
    company_types: List[str] = Field(default=[], description="公司类型（创业/成熟/大厂）")
    job_types: List[str] = Field(default=[], description="工作类型（全职/兼职/远程）")
    salary_min: Optional[int] = Field(None, description="最低期望薪资")
    salary_max: Optional[int] = Field(None, description="最高期望薪资")
    work_life_balance_priority: float = Field(0.5, ge=0, le=1, description="工作生活平衡权重")
    growth_priority: float = Field(0.5, ge=0, le=1, description="成长机会权重")


class SearchRequest(BaseModel):
    """搜索请求"""
    resume_id: int = Field(..., description="简历ID")
    preferences: Optional[SearchPreferences] = None
    limit: int = Field(20, ge=1, le=100, description="返回结果数量")


class JobMatchResult(BaseModel):
    """单个职位匹配结果"""
    job_id: int
    job_title: str
    company_name: str
    salary: Optional[str] = None
    location: str
    job_url: Optional[str] = None
    
    # 匹配得分
    overall_score: float = Field(..., ge=0, le=100, description="综合得分")
    dimension_scores: Dict[str, float] = Field(..., description="7维度得分")
    
    # 匹配详情
    match_details: Dict[str, Any] = Field(..., description="匹配详情")
    explanation: str = Field(..., description="推荐理由")
    recommendation: str = Field(..., description="推荐建议")


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool
    search_history_id: int
    total_jobs: int
    results: List[JobMatchResult]
    search_strategy: Dict[str, Any] = Field(..., description="搜索策略详情")
    improvement_suggestions: Optional[Dict[str, Any]] = None
    message: str
