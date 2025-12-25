"""
匹配记录模型 - 支持快速匹配和精细匹配
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime

from backend.database.connection import Base


class MatchRecord(Base):
    """匹配记录模型"""
    
    __tablename__ = "match_records"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 关联
    resume_id = Column(Integer, ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 匹配方式
    match_method = Column(String(20), nullable=False, comment="匹配方式: fast 或 precise")
    
    # 快速匹配结果（规则+Embedding）
    fast_score = Column(Float, nullable=True, index=True, comment="快速匹配分数 0-100")
    fast_details = Column(JSONB, nullable=True, comment="快速匹配详情")
    
    # 精细匹配结果（大模型）
    precise_score = Column(Float, nullable=True, index=True, comment="精细匹配分数 0-100")
    precise_analysis = Column(Text, nullable=True, comment="大模型分析文本")
    precise_details = Column(JSONB, nullable=True, comment="大模型分析详情")
    
    # 时间戳
    matched_at = Column(DateTime(timezone=True), server_default=func.now(), comment="匹配时间")
    
    # 唯一约束：一个简历+职位+匹配方式只能有一条记录
    __table_args__ = (
        UniqueConstraint('resume_id', 'job_id', 'match_method', name='uq_resume_job_method'),
    )
    
    def __repr__(self):
        return f"<MatchRecord(resume_id={self.resume_id}, job_id={self.job_id}, method={self.match_method})>"
    
    def to_dict(self):
        """转换为字典"""
        result = {
            'id': self.id,
            'resume_id': self.resume_id,
            'job_id': self.job_id,
            'match_method': self.match_method,
            'matched_at': self.matched_at.isoformat() if self.matched_at else None,
        }
        
        if self.match_method == 'fast' or self.fast_score is not None:
            result['fast_score'] = self.fast_score
            result['fast_details'] = self.fast_details
        
        if self.match_method == 'precise' or self.precise_score is not None:
            result['precise_score'] = self.precise_score
            result['precise_analysis'] = self.precise_analysis
            result['precise_details'] = self.precise_details
        
        return result
