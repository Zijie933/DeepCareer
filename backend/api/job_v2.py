"""
职位API V2 - 支持规则提取和大模型提取
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from pydantic import BaseModel

from backend.database.connection import get_db
from backend.models.job_v2 import JobV2
from backend.services.extractor_service import ExtractorService
from backend.utils.local_embedding import LocalEmbeddingService
from backend.utils.logger import logger

router = APIRouter(prefix="/api/v2/jobs", tags=["职位V2"])

extractor = ExtractorService()
embedding_service = LocalEmbeddingService()


class JobCreateRequest(BaseModel):
    """职位创建请求"""
    title: str
    company_name: str
    full_description: str  # 完整职位描述
    platform: Optional[str] = "manual"
    external_id: Optional[str] = None
    job_url: Optional[str] = None
    use_llm: bool = False  # 是否使用大模型提取


@router.post("/")
async def create_job(
    request: JobCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    创建职位（自动提取结构化数据）
    
    Args:
        request: 职位创建请求
    
    Returns:
        {
            "id": 职位ID,
            "structured_data": 结构化数据,
            "extraction_method": "rule" 或 "llm",
            "extraction_confidence": 置信度
        }
    """
    logger.info(f"创建职位: {request.title}, use_llm={request.use_llm}")
    
    # 检查是否已存在
    if request.external_id:
        result = await db.execute(
            select(JobV2).where(JobV2.external_id == request.external_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"职位已存在: {existing.id}")
            return existing.to_dict()
    
    # 智能提取结构化数据
    structured_data, confidence, method = extractor.extract_job(
        text=request.full_description,
        use_llm=request.use_llm,
        force_llm=False
    )
    
    # 补充基本信息（如果提取失败）
    if 'title' not in structured_data or not structured_data['title']:
        structured_data['title'] = request.title
    if 'company' not in structured_data or not structured_data['company']:
        structured_data['company'] = request.company_name
    
    # 生成向量
    try:
        embedding = embedding_service.create_embedding(request.full_description[:1000])
    except Exception as e:
        logger.warning(f"向量生成失败: {e}")
        embedding = None
    
    # 保存到数据库
    job = JobV2(
        external_id=request.external_id,
        platform=request.platform,
        job_url=request.job_url,
        title=structured_data.get('title', request.title),
        company_name=structured_data.get('company', request.company_name),
        city=structured_data.get('city'),
        salary_text=structured_data.get('salary_range'),
        experience_required=structured_data.get('experience_required'),
        education_required=structured_data.get('education_required'),
        full_description=request.full_description,
        structured_data=structured_data,
        extraction_method=method,
        extraction_confidence=confidence,
        description_embedding=embedding,
        is_active=True
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    logger.info(f"职位保存成功: ID={job.id}, method={method}, confidence={confidence:.2f}")
    
    return {
        "id": job.id,
        "structured_data": structured_data,
        "extraction_method": method,
        "extraction_confidence": round(confidence, 2)
    }


@router.get("/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """获取职位详情"""
    result = await db.execute(select(JobV2).where(JobV2.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    return job.to_dict()


@router.get("/")
async def list_jobs(
    keyword: Optional[str] = None,
    city: Optional[str] = None,
    platform: Optional[str] = None,
    salary_min: Optional[str] = None,
    experience: Optional[str] = None,
    education: Optional[str] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    获取职位列表（支持搜索和筛选）
    
    Args:
        keyword: 搜索关键词（匹配职位名称、公司名称）
        city: 城市筛选
        platform: 平台筛选
        salary_min: 最低薪资筛选
        experience: 经验要求筛选
        education: 学历要求筛选
        is_active: 是否活跃
        skip: 跳过数量
        limit: 返回数量
    """
    from sqlalchemy import or_
    
    # 构建查询
    query = select(JobV2).where(JobV2.is_active == is_active)
    count_query = select(func.count()).select_from(JobV2).where(JobV2.is_active == is_active)
    
    # 关键词搜索（职位名称或公司名称）
    if keyword:
        keyword_filter = or_(
            JobV2.title.ilike(f"%{keyword}%"),
            JobV2.company_name.ilike(f"%{keyword}%")
        )
        query = query.where(keyword_filter)
        count_query = count_query.where(keyword_filter)
    
    # 城市筛选（模糊匹配）
    if city:
        city_filter = JobV2.city.ilike(f"%{city}%")
        query = query.where(city_filter)
        count_query = count_query.where(city_filter)
    
    # 平台筛选
    if platform:
        query = query.where(JobV2.platform == platform)
        count_query = count_query.where(JobV2.platform == platform)
    
    # 经验要求筛选
    if experience:
        exp_filter = JobV2.experience_required.ilike(f"%{experience}%")
        query = query.where(exp_filter)
        count_query = count_query.where(exp_filter)
    
    # 学历要求筛选
    if education:
        edu_filter = JobV2.education_required.ilike(f"%{education}%")
        query = query.where(edu_filter)
        count_query = count_query.where(edu_filter)
    
    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 获取数据（按爬取时间倒序）
    query = query.order_by(JobV2.crawled_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return {
        "total": total,
        "items": [j.to_dict() for j in jobs]
    }


@router.post("/batch")
async def batch_create_jobs(
    jobs_data: list[JobCreateRequest],
    db: AsyncSession = Depends(get_db)
):
    """
    批量创建职位（爬虫使用）
    
    Args:
        jobs_data: 职位列表
    
    Returns:
        创建结果统计
    """
    logger.info(f"批量创建职位: {len(jobs_data)}条")
    
    created = 0
    skipped = 0
    failed = 0
    
    for job_req in jobs_data:
        try:
            # 检查是否存在
            if job_req.external_id:
                result = await db.execute(
                    select(JobV2).where(JobV2.external_id == job_req.external_id)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    skipped += 1
                    continue
            
            # 提取
            structured_data, confidence, method = extractor.extract_job(
                text=job_req.full_description,
                use_llm=False,  # 批量时不使用大模型
                force_llm=False
            )
            
            # 补充
            if 'title' not in structured_data:
                structured_data['title'] = job_req.title
            if 'company' not in structured_data:
                structured_data['company'] = job_req.company_name
            
            # 向量
            try:
                embedding = embedding_service.create_embedding(job_req.full_description[:1000])
            except:
                embedding = None
            
            # 保存
            job = JobV2(
                external_id=job_req.external_id,
                platform=job_req.platform,
                job_url=job_req.job_url,
                title=structured_data.get('title', job_req.title),
                company_name=structured_data.get('company', job_req.company_name),
                city=structured_data.get('city'),
                full_description=job_req.full_description,
                structured_data=structured_data,
                extraction_method=method,
                extraction_confidence=confidence,
                description_embedding=embedding,
                is_active=True
            )
            
            db.add(job)
            created += 1
        
        except Exception as e:
            logger.error(f"职位创建失败: {e}")
            failed += 1
    
    await db.commit()
    
    logger.info(f"批量创建完成: 成功{created}, 跳过{skipped}, 失败{failed}")
    
    return {
        "total": len(jobs_data),
        "created": created,
        "skipped": skipped,
        "failed": failed
    }
