"""
匹配API V2 - 支持快速匹配和精细匹配
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from pydantic import BaseModel

from backend.database.connection import get_db
from backend.models.resume_v2 import ResumeV2
from backend.models.job_v2 import JobV2
from backend.models.match_record import MatchRecord
from backend.services.matcher_service import MatcherService
from backend.utils.logger import logger

router = APIRouter(prefix="/api/v2/match", tags=["匹配V2"])

matcher = MatcherService()


class FastMatchRequest(BaseModel):
    """快速匹配请求"""
    resume_id: int
    job_ids: Optional[List[int]] = None  # 如果为空，匹配所有活跃职位
    top_k: int = 10


class PreciseMatchRequest(BaseModel):
    """精细匹配请求"""
    resume_id: int
    job_id: int


@router.post("/fast")
async def fast_match(
    request: FastMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    快速匹配（规则+Embedding）
    
    适用场景：
    - 初次筛选，快速找到Top N职位
    - 大批量匹配
    - 实时响应
    
    特点：
    - 速度快（毫秒级）
    - 成本低（无API调用）
    - 准确度中等（80%）
    
    Args:
        request: 匹配请求
    
    Returns:
        匹配结果列表，按分数降序
    """
    logger.info(f"快速匹配: resume_id={request.resume_id}, top_k={request.top_k}")
    
    # 1. 获取简历
    result = await db.execute(select(ResumeV2).where(ResumeV2.id == request.resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    if not resume.user_confirmed:
        raise HTTPException(status_code=400, detail="简历未确认，请先确认简历信息")
    
    # 2. 获取职位列表
    if request.job_ids:
        job_result = await db.execute(
            select(JobV2).where(
                JobV2.id.in_(request.job_ids),
                JobV2.is_active == True
            )
        )
    else:
        job_result = await db.execute(
            select(JobV2).where(JobV2.is_active == True).limit(100)
        )
    
    jobs = job_result.scalars().all()
    
    if not jobs:
        return {"matches": [], "total": 0}
    
    logger.info(f"找到{len(jobs)}个职位待匹配")
    
    # 3. 批量匹配
    results = []
    
    for job in jobs:
        # 检查是否已有缓存
        cache_result = await db.execute(
            select(MatchRecord).where(
                MatchRecord.resume_id == resume.id,
                MatchRecord.job_id == job.id,
                MatchRecord.match_method == 'fast'
            )
        )
        cached = cache_result.scalar_one_or_none()
        
        if cached:
            # 使用缓存
            results.append({
                'job_id': job.id,
                'job_title': job.title,
                'company_name': job.company_name,
                'city': job.city,
                'salary_text': job.salary_text,
                'match_score': cached.fast_score,
                'match_details': cached.fast_details,
                'from_cache': True
            })
        else:
            # 执行匹配
            try:
                score, details = matcher.fast_match(
                    resume_data=resume.structured_data,
                    job_data=job.structured_data,
                    resume_embedding=resume.text_embedding,
                    job_embedding=job.description_embedding
                )
                
                # 保存匹配记录
                match_record = MatchRecord(
                    resume_id=resume.id,
                    job_id=job.id,
                    match_method='fast',
                    fast_score=score,
                    fast_details=details
                )
                db.add(match_record)
                
                results.append({
                    'job_id': job.id,
                    'job_title': job.title,
                    'company_name': job.company_name,
                    'city': job.city,
                    'salary_text': job.salary_text,
                    'match_score': score,
                    'match_details': details,
                    'from_cache': False
                })
            
            except Exception as e:
                logger.error(f"匹配失败 job_id={job.id}: {e}")
                continue
    
    await db.commit()
    
    # 4. 排序并返回Top K
    results.sort(key=lambda x: x['match_score'], reverse=True)
    top_results = results[:request.top_k]
    
    logger.info(f"快速匹配完成，返回{len(top_results)}个结果")
    
    return {
        "matches": top_results,
        "total": len(results),
        "top_k": len(top_results)
    }


@router.post("/precise")
async def precise_match(
    request: PreciseMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    精细匹配（大模型深度分析）
    
    适用场景：
    - 已筛选出候选职位，需要深度分析
    - 用户明确要求精准匹配
    - 最终决策参考
    
    特点：
    - 准确度高（95%+）
    - 可解释性强
    - 多维度分析
    - 有成本（调用OpenAI API）
    
    Args:
        request: 精细匹配请求
    
    Returns:
        详细匹配报告
    """
    logger.info(f"精细匹配: resume_id={request.resume_id}, job_id={request.job_id}")
    
    # 1. 获取简历和职位
    resume_result = await db.execute(select(ResumeV2).where(ResumeV2.id == request.resume_id))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    job_result = await db.execute(select(JobV2).where(JobV2.id == request.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    # 2. 检查缓存
    cache_result = await db.execute(
        select(MatchRecord).where(
            MatchRecord.resume_id == resume.id,
            MatchRecord.job_id == job.id,
            MatchRecord.match_method == 'precise'
        )
    )
    cached = cache_result.scalar_one_or_none()
    
    if cached:
        logger.info("使用缓存的精细匹配结果")
        return {
            'job_id': job.id,
            'job_title': job.title,
            'company_name': job.company_name,
            'match_score': cached.precise_score,
            'analysis': cached.precise_analysis,
            'details': cached.precise_details,
            'from_cache': True
        }
    
    # 3. 执行精细匹配
    try:
        score, analysis_text, details = matcher.precise_match(
            resume_data=resume.structured_data,
            job_data=job.structured_data,
            resume_text=resume.full_text,
            job_text=job.full_description
        )
        
        # 4. 保存匹配记录
        match_record = MatchRecord(
            resume_id=resume.id,
            job_id=job.id,
            match_method='precise',
            precise_score=score,
            precise_analysis=analysis_text,
            precise_details=details
        )
        db.add(match_record)
        await db.commit()
        
        logger.info(f"精细匹配完成: score={score}")
        
        return {
            'job_id': job.id,
            'job_title': job.title,
            'company_name': job.company_name,
            'city': job.city,
            'salary_text': job.salary_text,
            'match_score': score,
            'analysis': analysis_text,
            'details': details,
            'from_cache': False
        }
    
    except Exception as e:
        logger.error(f"精细匹配失败: {e}")
        raise HTTPException(status_code=500, detail=f"匹配失败: {str(e)}")


@router.get("/history/{resume_id}")
async def get_match_history(
    resume_id: int,
    match_method: Optional[str] = Query(None, regex="^(fast|precise)$"),
    min_score: float = 0.0,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    获取匹配历史记录
    
    Args:
        resume_id: 简历ID
        match_method: 匹配方式（fast/precise）
        min_score: 最低分数筛选
        skip: 跳过条数
        limit: 返回条数
    """
    # 构建查询
    query = select(MatchRecord).where(MatchRecord.resume_id == resume_id)
    
    if match_method:
        query = query.where(MatchRecord.match_method == match_method)
    
    if match_method == 'fast' or not match_method:
        query = query.where(MatchRecord.fast_score >= min_score)
    else:
        query = query.where(MatchRecord.precise_score >= min_score)
    
    # 获取总数
    count_query = select(func.count()).select_from(MatchRecord).where(MatchRecord.resume_id == resume_id)
    if match_method:
        count_query = count_query.where(MatchRecord.match_method == match_method)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 按分数降序
    if match_method == 'fast':
        query = query.order_by(MatchRecord.fast_score.desc())
    elif match_method == 'precise':
        query = query.order_by(MatchRecord.precise_score.desc())
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()
    
    # 关联职位信息
    results = []
    for record in records:
        job_result = await db.execute(select(JobV2).where(JobV2.id == record.job_id))
        job = job_result.scalar_one_or_none()
        if job:
            results.append({
                'match_id': record.id,
                'job_id': job.id,
                'job_title': job.title,
                'company_name': job.company_name,
                'city': job.city,
                'match_method': record.match_method,
                'match_score': record.fast_score if record.match_method == 'fast' else record.precise_score,
                'matched_at': record.matched_at.isoformat() if record.matched_at else None
            })
    
    return {
        "total": total,
        "items": results
    }


@router.get("/stats/{resume_id}")
async def get_match_stats(
    resume_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取匹配统计信息
    
    Returns:
        {
            "total_matches": 总匹配数,
            "fast_matches": 快速匹配数,
            "precise_matches": 精细匹配数,
            "avg_fast_score": 快速匹配平均分,
            "avg_precise_score": 精细匹配平均分,
            "high_match_count": 高匹配度数量(>=80分),
            "medium_match_count": 中等匹配度数量(60-80分),
            "low_match_count": 低匹配度数量(<60分)
        }
    """
    # 总数
    total_result = await db.execute(
        select(func.count()).select_from(MatchRecord).where(MatchRecord.resume_id == resume_id)
    )
    total = total_result.scalar()
    
    # 快速匹配统计
    fast_count_result = await db.execute(
        select(func.count()).select_from(MatchRecord).where(
            MatchRecord.resume_id == resume_id,
            MatchRecord.match_method == 'fast'
        )
    )
    fast_count = fast_count_result.scalar()
    
    fast_avg_result = await db.execute(
        select(func.avg(MatchRecord.fast_score)).where(
            MatchRecord.resume_id == resume_id,
            MatchRecord.match_method == 'fast'
        )
    )
    fast_avg = fast_avg_result.scalar() or 0
    
    # 精细匹配统计
    precise_count_result = await db.execute(
        select(func.count()).select_from(MatchRecord).where(
            MatchRecord.resume_id == resume_id,
            MatchRecord.match_method == 'precise'
        )
    )
    precise_count = precise_count_result.scalar()
    
    precise_avg_result = await db.execute(
        select(func.avg(MatchRecord.precise_score)).where(
            MatchRecord.resume_id == resume_id,
            MatchRecord.match_method == 'precise'
        )
    )
    precise_avg = precise_avg_result.scalar() or 0
    
    # 分数段统计（以快速匹配为准）
    high_count_result = await db.execute(
        select(func.count()).select_from(MatchRecord).where(
            MatchRecord.resume_id == resume_id,
            MatchRecord.match_method == 'fast',
            MatchRecord.fast_score >= 80
        )
    )
    high_count = high_count_result.scalar()
    
    medium_count_result = await db.execute(
        select(func.count()).select_from(MatchRecord).where(
            MatchRecord.resume_id == resume_id,
            MatchRecord.match_method == 'fast',
            MatchRecord.fast_score >= 60,
            MatchRecord.fast_score < 80
        )
    )
    medium_count = medium_count_result.scalar()
    
    low_count_result = await db.execute(
        select(func.count()).select_from(MatchRecord).where(
            MatchRecord.resume_id == resume_id,
            MatchRecord.match_method == 'fast',
            MatchRecord.fast_score < 60
        )
    )
    low_count = low_count_result.scalar()
    
    return {
        "total_matches": total,
        "fast_matches": fast_count,
        "precise_matches": precise_count,
        "avg_fast_score": round(float(fast_avg), 2),
        "avg_precise_score": round(float(precise_avg), 2),
        "high_match_count": high_count,
        "medium_match_count": medium_count,
        "low_match_count": low_count
    }
