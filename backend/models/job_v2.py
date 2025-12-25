"""
职位模型 V2 - 支持规则提取和大模型提取
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime

try:
    from pgvector.sqlalchemy import Vector as VECTOR
except ImportError:
    # 如果pgvector未安装，使用Text作为后备
    VECTOR = lambda dim: Text

from backend.database.connection import Base
from backend.config import settings


class JobV2(Base):
    """职位模型 V2"""
    
    __tablename__ = "jobs"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 外部标识
    external_id = Column(String(100), unique=True, index=True, comment="外部平台职位ID")
    platform = Column(String(50), index=True, comment="招聘平台")
    job_url = Column(String(500), nullable=True, comment="职位详情URL")
    
    # 基本信息
    title = Column(String(255), nullable=False, index=True, comment="职位名称")
    company_name = Column(String(255), nullable=False, index=True, comment="公司名称")
    city = Column(String(50), index=True, comment="城市")
    district = Column(String(50), nullable=True, comment="区域")
    
    # 薪资
    salary_min = Column(Integer, nullable=True, comment="最低薪资")
    salary_max = Column(Integer, nullable=True, comment="最高薪资")
    salary_text = Column(String(100), nullable=True, comment="薪资文本")
    
    # 要求
    experience_required = Column(String(50), nullable=True, comment="经验要求")
    education_required = Column(String(50), nullable=True, comment="学历要求")
    
    # 原始描述
    full_description = Column(Text, nullable=True, comment="完整职位描述")
    
    # 结构化数据（核心）
    structured_data = Column(JSONB, nullable=False, default={}, comment="结构化职位数据")
    
    # 提取元数据
    extraction_method = Column(
        String(20), 
        nullable=False, 
        default='rule', 
        comment="提取方法: rule 或 llm"
    )
    extraction_confidence = Column(Float, default=0.0, comment="提取置信度 0-1")
    extracted_at = Column(DateTime(timezone=True), default=datetime.utcnow, comment="提取时间")
    
    # 向量字段
    description_embedding = Column(
        VECTOR(settings.EMBEDDING_DIMENSION),
        nullable=True,
        comment="职位描述向量"
    )
    
    # 状态
    is_active = Column(Boolean, default=True, index=True, comment="是否有效")
    
    # 时间戳
    posted_at = Column(DateTime(timezone=True), nullable=True, comment="发布时间")
    crawled_at = Column(DateTime(timezone=True), server_default=func.now(), comment="爬取时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self):
        return f"<Job(id={self.id}, title={self.title}, company={self.company_name})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'external_id': self.external_id,
            'platform': self.platform,
            'job_url': self.job_url,
            'title': self.title,
            'company_name': self.company_name,
            'city': self.city,
            'district': self.district,
            'salary_text': self.salary_text,
            'experience_required': self.experience_required,
            'education_required': self.education_required,
            'full_description': self.full_description,
            'structured_data': self.structured_data,
            'extraction_method': self.extraction_method,
            'extraction_confidence': self.extraction_confidence,
            'is_active': self.is_active,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'created_at': self.crawled_at.isoformat() if self.crawled_at else None,
        }
