"""
职位搜索 API
"""
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from backend.database import get_db
from backend.models.resume_v2 import ResumeV2 as Resume
from backend.models.job_v2 import JobV2 as Job
from backend.models.search_history import SearchHistory
from backend.schemas.search import (
    SearchRequest,
    SearchResponse,
    JobMatchResult,
    SearchPreferences,
)
from backend.agents.search_strategy import search_strategy
from backend.agents.job_matcher import job_matcher
from backend.agents.reasoning_agent import reasoning_agent
from backend.services.feedback_learner import feedback_learner
from backend.config import settings

router = APIRouter(prefix="/api/search", tags=["搜索"])


@router.post("", response_model=SearchResponse)
async def search_jobs(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    智能职位搜索
    
    流程：
    1. 获取简历分析结果
    2. 制定搜索策略
    3. 检索候选职位（Mock数据 - 实际应调用职位爬虫）
    4. 智能匹配与评分
    5. 生成推荐理由
    6. 记录搜索历史
    """
    start_time = time.time()
    
    # 1. 获取简历
    result = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    resume = result.scalar_one_or_none()
    
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    if not resume.analysis_result:
        raise HTTPException(status_code=400, detail="请先解析简历")
    
    try:
        # 2. 分析用户偏好（基于历史反馈）
        user_preferences = await feedback_learner.analyze_user_preferences(
            resume_id=request.resume_id,
            db=db,
        )
        
        # 使用优化后的权重
        optimized_weights = user_preferences.get("optimized_weights", settings.DIMENSION_WEIGHTS)
        
        # 3. 制定搜索策略
        preferences = request.preferences or SearchPreferences()
        search_plan = await search_strategy.plan_search(
            candidate_profile=resume.analysis_result,
            preferences=preferences.dict(),
        )
        
        # 合并策略权重和用户偏好权重
        dimension_weights = search_plan.get("dimension_weights", optimized_weights)
        
        logger.info(f"搜索策略制定完成 - resume_id: {request.resume_id}")
        
        # 3. 检索职位（这里使用数据库中的Mock职位）
        # 实际使用时应调用 JobCrawler 爬取最新职位
        jobs_query = select(Job).where(Job.is_active == True).limit(request.limit)
        jobs_result = await db.execute(jobs_query)
        jobs = list(jobs_result.scalars().all())
        
        if not jobs:
            logger.warning("数据库中没有职位数据，返回空结果")
            return SearchResponse(
                success=True,
                search_history_id=0,
                total_jobs=0,
                results=[],
                search_strategy=search_plan,
                message="暂无匹配职位（数据库为空）",
            )
        
        # 4. 智能匹配
        match_results = await job_matcher.batch_match(
            jobs=jobs,
            candidate_profile=resume.analysis_result,
            weights=dimension_weights,
        )
        
        # 5. 组合结果并生成推荐理由
        combined_results = []
        for job, match_result in zip(jobs, match_results):
            # 生成推荐理由
            job_info = {
                "title": job.title,
                "company": job.company_name,
                "salary": f"{job.salary_min}-{job.salary_max}" if job.salary_min else job.salary_text,
                "location": f"{job.city} {job.district or ''}".strip(),
            }
            
            explanation = await reasoning_agent.explain_match(
                job_info=job_info,
                candidate_profile=resume.analysis_result,
                match_result=match_result,
            )
            
            combined_results.append({
                "job": job,
                "match_result": match_result,
                "explanation": explanation,
            })
        
        # 6. 按综合得分排序
        combined_results.sort(
            key=lambda x: x["match_result"]["overall_score"],
            reverse=True
        )
        
        # 7. 生成改进建议
        top_match_results = [r["match_result"] for r in combined_results[:5]]
        improvement_suggestions = await reasoning_agent.suggest_improvements(
            candidate_profile=resume.analysis_result,
            match_results=top_match_results,
        )
        
        # 8. 构建响应
        job_match_results = []
        for item in combined_results:
            job = item["job"]
            match_result = item["match_result"]
            
            job_match_results.append(JobMatchResult(
                job_id=job.id,
                job_title=job.title,
                company_name=job.company_name,
                salary=f"{job.salary_min}-{job.salary_max}" if job.salary_min else job.salary_text,
                location=f"{job.city} {job.district or ''}".strip(),
                job_url=job.job_url,
                overall_score=match_result["overall_score"],
                dimension_scores={
                    dim: match_result["dimensions"].get(dim, {}).get("score", 0)
                    for dim in dimension_weights.keys()
                },
                match_details=match_result["dimensions"],
                explanation=item["explanation"],
                recommendation=match_result.get("recommendation", ""),
            ))
        
        # 9. 保存搜索历史
        search_history = SearchHistory(
            resume_id=request.resume_id,
            search_params=preferences.dict(),
            strategy_type=search_plan.get("search_radius", "适中"),
            strategy_details=search_plan,
            total_jobs_found=len(jobs),
            jobs_returned=len(job_match_results),
            job_ids=[r.job_id for r in job_match_results],
            avg_match_score=sum(r.overall_score for r in job_match_results) / len(job_match_results) if job_match_results else 0,
            search_duration=time.time() - start_time,
        )
        
        db.add(search_history)
        await db.commit()
        await db.refresh(search_history)
        
        logger.info(
            f"搜索完成 - resume_id: {request.resume_id}, "
            f"职位数: {len(job_match_results)}, "
            f"耗时: {search_history.search_duration:.2f}s"
        )
        
        return SearchResponse(
            success=True,
            search_history_id=search_history.id,
            total_jobs=len(jobs),
            results=job_match_results,
            search_strategy=search_plan,
            improvement_suggestions=improvement_suggestions,
            message=f"成功匹配 {len(job_match_results)} 个职位",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
