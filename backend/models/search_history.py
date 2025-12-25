"""
搜索历史数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, ForeignKey
from sqlalchemy.sql import func

from backend.database.connection import Base


class SearchHistory(Base):
    """搜索历史模型"""
    
    __tablename__ = "search_histories"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 关联字段
    resume_id = Column(Integer, ForeignKey("resumes.id"), index=True, comment="简历ID")
    user_id = Column(String(100), index=True, nullable=True, comment="用户ID")
    
    # 搜索参数
    search_params = Column(JSON, nullable=True, comment="搜索参数（偏好设置等）")
    
    # 搜索策略
    strategy_type = Column(String(50), nullable=True, comment="搜索策略类型")
    strategy_details = Column(JSON, nullable=True, comment="策略详情")
    
    # 搜索结果统计
    total_jobs_found = Column(Integer, default=0, comment="找到的职位总数")
    jobs_returned = Column(Integer, default=0, comment="返回给用户的职位数")
    
    # 结果ID列表
    job_ids = Column(JSON, nullable=True, comment="返回的职位ID列表")
    
    # 平均匹配分数
    avg_match_score = Column(Float, nullable=True, comment="平均匹配分数")
    
    # 用户交互统计
    viewed_count = Column(Integer, default=0, comment="查看次数")
    liked_count = Column(Integer, default=0, comment="点赞次数")
    applied_count = Column(Integer, default=0, comment="申请次数")
    
    # 搜索耗时（秒）
    search_duration = Column(Float, nullable=True, comment="搜索耗时")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="创建时间")
    
    def __repr__(self):
        return f"<SearchHistory(id={self.id}, resume_id={self.resume_id}, jobs={self.total_jobs_found})>"
