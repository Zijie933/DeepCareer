"""
简历模型 V2 - 支持规则提取和大模型提取
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime

# pgvector 支持
try:
    from pgvector.sqlalchemy import Vector as VECTOR
except ImportError:
    # 如果pgvector未安装，使用Text作为后备
    VECTOR = lambda dim: Text

from backend.database.connection import Base
from backend.config import settings


class ResumeV2(Base):
    """简历模型 V2"""
    
    __tablename__ = "resumes"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 基本信息
    user_id = Column(String(100), index=True, nullable=True, comment="用户ID")
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    file_type = Column(String(20), nullable=False, comment="文件类型")
    
    # 原始文本
    full_text = Column(Text, nullable=True, comment="简历全文")
    
    # 结构化数据（核心）
    structured_data = Column(JSONB, nullable=False, default={}, comment="结构化简历数据")
    
    # 提取元数据
    extraction_method = Column(
        String(20), 
        nullable=False, 
        default='rule', 
        comment="提取方法: rule 或 llm"
    )
    extraction_confidence = Column(Float, default=0.0, comment="提取置信度 0-1")
    extracted_at = Column(DateTime(timezone=True), default=datetime.utcnow, comment="提取时间")
    
    # 用户确认状态
    user_confirmed = Column(Boolean, default=False, comment="用户是否已确认")
    confirmed_at = Column(DateTime(timezone=True), nullable=True, comment="确认时间")
    
    # 向量字段
    text_embedding = Column(
        VECTOR(settings.EMBEDDING_DIMENSION),
        nullable=True,
        comment="简历文本向量"
    )
    
    # AI分析结果（可选）
    ai_analysis = Column(JSONB, nullable=True, comment="AI分析结果")
    quality_score = Column(Float, nullable=True, comment="质量分数")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Resume(id={self.id}, name={self.structured_data.get('name', 'Unknown')})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'structured_data': self.structured_data,
            'extraction_method': self.extraction_method,
            'extraction_confidence': self.extraction_confidence,
            'user_confirmed': self.user_confirmed,
            'quality_score': self.quality_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
