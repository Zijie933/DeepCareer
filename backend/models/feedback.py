"""
用户反馈数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Text, ForeignKey
from sqlalchemy.sql import func

from backend.database.connection import Base


class UserFeedback(Base):
    """用户反馈模型"""
    
    __tablename__ = "user_feedbacks"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 关联字段
    resume_id = Column(Integer, ForeignKey("resumes.id"), index=True, comment="简历ID")
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, comment="职位ID")
    search_history_id = Column(Integer, ForeignKey("search_histories.id"), nullable=True, comment="搜索历史ID")
    
    # 反馈类型
    feedback_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="反馈类型（like/dislike/apply/view/share）"
    )
    
    # 评分
    rating = Column(Float, nullable=True, comment="评分（1-5）")
    
    # 文本反馈
    comment = Column(Text, nullable=True, comment="文字评论")
    
    # 反馈详情（JSON）
    feedback_details = Column(
        JSON,
        nullable=True,
        comment="详细反馈（7维度评分、不满意原因等）"
    )
    
    # 用户信息
    user_id = Column(String(100), index=True, nullable=True, comment="用户ID")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="创建时间")
    
    def __repr__(self):
        return f"<UserFeedback(id={self.id}, type={self.feedback_type}, job_id={self.job_id})>"
