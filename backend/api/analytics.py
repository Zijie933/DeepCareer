"""
分析与学习 API
提供基于反馈的数据分析和策略优化接口
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.database import get_db
from backend.models.resume_v2 import ResumeV2 as Resume
from backend.services.feedback_learner import feedback_learner

router = APIRouter(prefix="/api/analytics", tags=["分析"])


@router.get("/user-preferences/{resume_id}")
async def get_user_preferences(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户偏好分析
    
    基于历史反馈数据，分析用户在7个维度的偏好
    """
    # 验证简历存在
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="简历不存在")
    
    try:
        preferences = await feedback_learner.analyze_user_preferences(
            resume_id=resume_id,
            db=db,
        )
        
        return {
            "success": True,
            "resume_id": resume_id,
            "data": preferences,
        }
    
    except Exception as e:
        logger.error(f"用户偏好分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/recommendation-quality/{search_history_id}")
async def get_recommendation_quality(
    search_history_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取推荐质量评估
    
    分析某次搜索的推荐效果（参与率、转化率、评分等）
    """
    try:
        quality = await feedback_learner.calculate_recommendation_quality(
            search_history_id=search_history_id,
            db=db,
        )
        
        return {
            "success": True,
            "search_history_id": search_history_id,
            "quality": quality,
        }
    
    except Exception as e:
        logger.error(f"推荐质量评估失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.get("/top-strategies")
async def get_top_strategies(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """
    获取表现最好的搜索策略
    
    分析历史数据，找出转化率最高的策略
    """
    try:
        strategies = await feedback_learner.get_top_performing_strategies(
            db=db,
            limit=limit,
        )
        
        return {
            "success": True,
            "total": len(strategies),
            "strategies": strategies,
        }
    
    except Exception as e:
        logger.error(f"策略分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/strategy-suggestions/{resume_id}")
async def get_strategy_suggestions(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取策略改进建议
    
    基于用户反馈和最佳实践，给出个性化的搜索策略建议
    """
    # 验证简历存在
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="简历不存在")
    
    try:
        suggestions = await feedback_learner.suggest_strategy_improvements(
            resume_id=resume_id,
            db=db,
        )
        
        return {
            "success": True,
            "resume_id": resume_id,
            "suggestions": suggestions,
        }
    
    except Exception as e:
        logger.error(f"策略建议生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.get("/dashboard/{resume_id}")
async def get_analytics_dashboard(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户分析仪表盘
    
    综合展示用户的反馈数据、偏好分析、推荐质量等
    """
    # 验证简历存在
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="简历不存在")
    
    try:
        # 获取用户偏好
        preferences = await feedback_learner.analyze_user_preferences(
            resume_id=resume_id,
            db=db,
        )
        
        # 获取策略建议
        suggestions = await feedback_learner.suggest_strategy_improvements(
            resume_id=resume_id,
            db=db,
        )
        
        return {
            "success": True,
            "resume_id": resume_id,
            "dashboard": {
                "preferences": preferences,
                "suggestions": suggestions,
            },
        }
    
    except Exception as e:
        logger.error(f"仪表盘数据获取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")
