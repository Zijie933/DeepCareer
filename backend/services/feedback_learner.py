"""
反馈学习服务
基于用户反馈数据，动态优化推荐策略
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger
import numpy as np

from backend.models.feedback import UserFeedback
from backend.models.search_history import SearchHistory
from backend.config import settings


class FeedbackLearner:
    """反馈学习器"""
    
    def __init__(self):
        self.default_weights = settings.DIMENSION_WEIGHTS
        # 反馈类型权重（用于计算奖励）
        self.feedback_rewards = {
            "apply": 10.0,    # 申请职位：最高奖励
            "like": 5.0,      # 点赞：高奖励
            "view": 2.0,      # 查看：中等奖励
            "share": 3.0,     # 分享：较高奖励
            "dislike": -5.0,  # 不喜欢：负奖励
        }
    
    async def analyze_user_preferences(
        self,
        resume_id: int,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        分析用户偏好
        
        Args:
            resume_id: 简历ID
            db: 数据库会话
        
        Returns:
            Dict: {
                "preferred_dimensions": {...},  # 用户偏好的维度
                "optimized_weights": {...},     # 优化后的权重
                "feedback_summary": {...},      # 反馈摘要
            }
        """
        # 获取所有反馈
        feedbacks_query = select(UserFeedback).where(
            UserFeedback.resume_id == resume_id
        )
        result = await db.execute(feedbacks_query)
        feedbacks = list(result.scalars().all())
        
        if not feedbacks:
            logger.info(f"用户 {resume_id} 暂无反馈数据")
            return {
                "preferred_dimensions": {},
                "optimized_weights": self.default_weights,
                "feedback_summary": {
                    "total": 0,
                    "positive": 0,
                    "negative": 0,
                },
            }
        
        # 统计反馈类型
        feedback_counts = {}
        for fb in feedbacks:
            feedback_counts[fb.feedback_type] = feedback_counts.get(fb.feedback_type, 0) + 1
        
        positive_count = feedback_counts.get("like", 0) + feedback_counts.get("apply", 0)
        negative_count = feedback_counts.get("dislike", 0)
        
        # 分析7维度偏好
        dimension_scores = {dim: [] for dim in self.default_weights.keys()}
        
        for fb in feedbacks:
            if fb.feedback_details and isinstance(fb.feedback_details, dict):
                # 提取7维度评分
                for dim in dimension_scores.keys():
                    score = fb.feedback_details.get(dim)
                    if score is not None:
                        dimension_scores[dim].append(float(score))
        
        # 计算平均偏好
        preferred_dimensions = {}
        for dim, scores in dimension_scores.items():
            if scores:
                preferred_dimensions[dim] = {
                    "avg_score": np.mean(scores),
                    "std_score": np.std(scores),
                    "sample_count": len(scores),
                }
        
        # 优化权重
        optimized_weights = self._optimize_weights(
            feedbacks, preferred_dimensions
        )
        
        logger.info(
            f"用户偏好分析完成 - resume_id: {resume_id}, "
            f"反馈数: {len(feedbacks)}, "
            f"正向: {positive_count}, "
            f"负向: {negative_count}"
        )
        
        return {
            "preferred_dimensions": preferred_dimensions,
            "optimized_weights": optimized_weights,
            "feedback_summary": {
                "total": len(feedbacks),
                "positive": positive_count,
                "negative": negative_count,
                "counts": feedback_counts,
            },
        }
    
    def _optimize_weights(
        self,
        feedbacks: List[UserFeedback],
        preferred_dimensions: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        优化7维度权重
        
        策略：
        1. 用户高分维度增加权重
        2. 用户低分维度降低权重
        3. 正向反馈多的维度增加权重
        """
        optimized = self.default_weights.copy()
        
        if not preferred_dimensions:
            return optimized
        
        # 计算调整因子
        adjustments = {}
        for dim, stats in preferred_dimensions.items():
            if stats["sample_count"] < 3:  # 样本太少，不调整
                continue
            
            avg_score = stats["avg_score"]
            
            # 高分维度增加权重，低分维度降低权重
            if avg_score > 70:
                adjustments[dim] = 1.2  # 增加20%
            elif avg_score < 40:
                adjustments[dim] = 0.8  # 降低20%
            else:
                adjustments[dim] = 1.0
        
        # 应用调整
        for dim in optimized.keys():
            if dim in adjustments:
                optimized[dim] *= adjustments[dim]
        
        # 归一化
        total = sum(optimized.values())
        for dim in optimized:
            optimized[dim] = round(optimized[dim] / total, 2)
        
        logger.info(f"权重优化完成 - 调整: {adjustments}")
        
        return optimized
    
    async def calculate_recommendation_quality(
        self,
        search_history_id: int,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        计算推荐质量
        
        Args:
            search_history_id: 搜索历史ID
            db: 数据库会话
        
        Returns:
            Dict: {
                "quality_score": float,  # 质量分数（0-100）
                "engagement_rate": float,  # 参与率
                "conversion_rate": float,  # 转化率（申请率）
                "avg_rating": float,  # 平均评分
            }
        """
        # 获取搜索历史
        search_result = await db.execute(
            select(SearchHistory).where(SearchHistory.id == search_history_id)
        )
        search_history = search_result.scalar_one_or_none()
        
        if not search_history:
            logger.warning(f"搜索历史不存在: {search_history_id}")
            return {
                "quality_score": 0,
                "engagement_rate": 0,
                "conversion_rate": 0,
                "avg_rating": 0,
            }
        
        # 获取该次搜索的所有反馈
        feedbacks_query = select(UserFeedback).where(
            UserFeedback.search_history_id == search_history_id
        )
        result = await db.execute(feedbacks_query)
        feedbacks = list(result.scalars().all())
        
        if not feedbacks:
            return {
                "quality_score": 0,
                "engagement_rate": 0,
                "conversion_rate": 0,
                "avg_rating": 0,
            }
        
        total_jobs = search_history.jobs_returned or 1
        
        # 计算参与率（有互动的职位占比）
        engaged_jobs = len(set(fb.job_id for fb in feedbacks))
        engagement_rate = engaged_jobs / total_jobs
        
        # 计算转化率（申请的职位占比）
        applied_count = sum(1 for fb in feedbacks if fb.feedback_type == "apply")
        conversion_rate = applied_count / total_jobs
        
        # 计算平均评分
        ratings = [fb.rating for fb in feedbacks if fb.rating is not None]
        avg_rating = np.mean(ratings) if ratings else 0
        
        # 计算质量分数（加权平均）
        quality_score = (
            engagement_rate * 30 +  # 参与率占30%
            conversion_rate * 50 +   # 转化率占50%
            (avg_rating / 5) * 20    # 评分占20%
        ) * 100
        
        logger.info(
            f"推荐质量分析 - search_id: {search_history_id}, "
            f"质量分: {quality_score:.2f}, "
            f"参与率: {engagement_rate:.2%}, "
            f"转化率: {conversion_rate:.2%}"
        )
        
        return {
            "quality_score": round(quality_score, 2),
            "engagement_rate": round(engagement_rate, 4),
            "conversion_rate": round(conversion_rate, 4),
            "avg_rating": round(avg_rating, 2) if avg_rating else 0,
        }
    
    async def get_top_performing_strategies(
        self,
        db: AsyncSession,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        获取表现最好的搜索策略
        
        Args:
            db: 数据库会话
            limit: 返回数量
        
        Returns:
            List[Dict]: 策略列表
        """
        # 获取所有搜索历史（包含策略详情）
        query = select(SearchHistory).order_by(
            SearchHistory.created_at.desc()
        ).limit(100)  # 分析最近100次搜索
        
        result = await db.execute(query)
        histories = list(result.scalars().all())
        
        strategies_performance = []
        
        for history in histories:
            if not history.strategy_details:
                continue
            
            # 计算该策略的质量
            quality = await self.calculate_recommendation_quality(
                history.id, db
            )
            
            strategies_performance.append({
                "search_id": history.id,
                "strategy_type": history.strategy_type,
                "strategy_details": history.strategy_details,
                "quality_score": quality["quality_score"],
                "engagement_rate": quality["engagement_rate"],
                "conversion_rate": quality["conversion_rate"],
            })
        
        # 按质量分数排序
        strategies_performance.sort(
            key=lambda x: x["quality_score"],
            reverse=True
        )
        
        return strategies_performance[:limit]
    
    async def suggest_strategy_improvements(
        self,
        resume_id: int,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        基于反馈建议策略改进
        
        Args:
            resume_id: 简历ID
            db: 数据库会话
        
        Returns:
            Dict: 改进建议
        """
        # 分析用户偏好
        preferences = await self.analyze_user_preferences(resume_id, db)
        
        # 获取表现最好的策略
        top_strategies = await self.get_top_performing_strategies(db)
        
        suggestions = {
            "recommended_weights": preferences["optimized_weights"],
            "feedback_insights": preferences["feedback_summary"],
            "best_practices": [],
        }
        
        # 从最佳策略中提取建议
        if top_strategies:
            best_strategy = top_strategies[0]
            suggestions["best_practices"].append({
                "description": f"参考高质量策略（质量分: {best_strategy['quality_score']:.2f}）",
                "strategy_type": best_strategy["strategy_type"],
                "key_points": best_strategy["strategy_details"].get("rationale", ""),
            })
        
        logger.info(f"策略改进建议生成完成 - resume_id: {resume_id}")
        
        return suggestions


# 创建全局实例
feedback_learner = FeedbackLearner()
