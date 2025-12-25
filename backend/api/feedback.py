"""
用户反馈 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.database import get_db
from backend.models.feedback import UserFeedback
from backend.models.resume_v2 import ResumeV2 as Resume
from backend.models.job_v2 import JobV2 as Job
from backend.schemas.feedback import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/feedback", tags=["反馈"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    提交用户反馈
    
    反馈类型：
    - like: 喜欢这个职位
    - dislike: 不喜欢这个职位
    - apply: 已申请该职位
    - view: 查看了职位详情
    - share: 分享了职位
    """
    # 验证反馈类型
    allowed_types = ["like", "dislike", "apply", "view", "share"]
    if request.feedback_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的反馈类型。允许的类型: {', '.join(allowed_types)}"
        )
    
    # 验证简历存在
    resume_result = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    if not resume_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="简历不存在")
    
    # 验证职位存在
    job_result = await db.execute(select(Job).where(Job.id == request.job_id))
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="职位不存在")
    
    try:
        # 创建反馈记录
        feedback = UserFeedback(
            resume_id=request.resume_id,
            job_id=request.job_id,
            search_history_id=request.search_history_id,
            feedback_type=request.feedback_type,
            rating=request.rating,
            comment=request.comment,
            feedback_details=request.feedback_details,
        )
        
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        
        logger.info(
            f"用户反馈提交成功 - "
            f"feedback_id: {feedback.id}, "
            f"type: {request.feedback_type}, "
            f"job_id: {request.job_id}"
        )
        
        return FeedbackResponse(
            success=True,
            feedback_id=feedback.id,
            message="反馈提交成功",
        )
    
    except Exception as e:
        logger.error(f"反馈提交失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


@router.get("/stats/{resume_id}")
async def get_feedback_stats(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户反馈统计
    """
    from sqlalchemy import func
    
    # 统计各类反馈数量
    stats_query = select(
        UserFeedback.feedback_type,
        func.count(UserFeedback.id).label("count")
    ).where(
        UserFeedback.resume_id == resume_id
    ).group_by(
        UserFeedback.feedback_type
    )
    
    result = await db.execute(stats_query)
    stats = {row.feedback_type: row.count for row in result}
    
    return {
        "resume_id": resume_id,
        "stats": stats,
        "total": sum(stats.values()),
    }
