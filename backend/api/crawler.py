"""
爬虫API - 职位抓取和入库（Playwright版，支持Cookie）
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import asyncio
from pydantic import BaseModel

from backend.database.connection import get_db
from backend.crawlers.boss_web_crawler_playwright import BossWebCrawlerPlaywright
from backend.models.job_v2 import JobV2
from backend.services.extractor_service import ExtractorService
from backend.utils.local_embedding import LocalEmbeddingService
from backend.utils.logger import logger
from backend.config import settings

router = APIRouter(prefix="/api/crawler", tags=["爬虫"])

extractor = ExtractorService()
embedding_service = LocalEmbeddingService()


class CrawlRequest(BaseModel):
    """爬虫请求"""
    keyword: str  # 搜索关键词
    city: str = "深圳"  # 城市
    max_results: int = 30  # 最大结果数（增加默认值）
    fetch_detail: bool = True  # 是否获取详情页
    save_to_db: bool = True  # 是否保存到数据库
    max_concurrent: int = 5  # 最大并发数
    cookie_string: Optional[str] = None  # 自定义Cookie
    auto_scroll: bool = True  # 是否滚动加载更多
    max_scroll: int = 5  # 最大滚动次数


class CrawlResponse(BaseModel):
    """爬虫响应"""
    total_found: int  # 找到的职位数
    saved_count: int  # 保存的职位数
    skipped_count: int  # 跳过的职位数（已存在）
    failed_count: int  # 失败的职位数
    jobs: list  # 职位列表


@router.post("/boss/search", response_model=CrawlResponse)
async def crawl_boss_jobs(
    request: CrawlRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    爬取BOSS直聘职位（Playwright版，支持Cookie）
    
    Args:
        request: 爬虫请求参数
    
    Returns:
        爬取结果统计和职位列表
    """
    logger.info(f"🚀 开始爬取BOSS直聘: keyword={request.keyword}, city={request.city}")
    
    cookie = request.cookie_string or settings.BOSS_COOKIE
    
    if not cookie:
        raise HTTPException(
            status_code=400, 
            detail="未配置Cookie，请通过环境变量BOSS_COOKIE设置或在请求中传入cookie_string"
        )
    
    async with BossWebCrawlerPlaywright(
        min_delay=1.5,
        max_delay=3.0,
        headless=True,
        cookie_string=cookie,
        target_city=request.city
    ) as crawler:
        try:
            # 1. 搜索职位列表（根据参数决定是否滚动）
            all_jobs = await crawler.search_jobs(
                keyword=request.keyword,
                city=request.city,
                page=1,
                auto_scroll=request.auto_scroll,
                max_scroll=request.max_scroll
            )
            
            if not all_jobs:
                logger.warning("未爬取到任何职位")
                return CrawlResponse(
                    total_found=0,
                    saved_count=0,
                    skipped_count=0,
                    failed_count=0,
                    jobs=[]
                )
            
            # 限制数量
            jobs_to_fetch = all_jobs[:request.max_results]
            
            # 2. 获取详情（可选）
            if request.fetch_detail:
                logger.info(f"📥 开始获取 {len(jobs_to_fetch)} 个职位的详情（并发数: {request.max_concurrent}）...")
                
                semaphore = asyncio.Semaphore(request.max_concurrent)
                
                async def fetch_detail(job, index):
                    async with semaphore:
                        job_url = job.get("job_url")
                        if not job_url:
                            return job
                        
                        detail = await crawler.get_job_detail(job_url, use_random_ua=True)
                        if detail:
                            job.update(detail)
                        
                        return job
                
                jobs = await asyncio.gather(
                    *[fetch_detail(job, idx) for idx, job in enumerate(jobs_to_fetch, 1)],
                    return_exceptions=True
                )
                
                # 过滤异常
                jobs = [j for j in jobs if not isinstance(j, Exception)]
            else:
                jobs = jobs_to_fetch
            
            logger.info(f"✅ 爬取成功: 共 {len(jobs)} 个职位")
            logger.info(f"📊 爬虫统计: {crawler.get_stats()}")
            
            # 3. 保存到数据库（可选）
            saved_count = 0
            skipped_count = 0
            failed_count = 0
            
            if request.save_to_db:
                for job in jobs:
                    try:
                        # 检查是否已存在
                        job_id = job.get('job_id', '')
                        if job_id:
                            result = await db.execute(
                                select(JobV2).where(JobV2.external_id == job_id)
                            )
                            existing = result.scalar_one_or_none()
                            if existing:
                                logger.debug(f"职位已存在，跳过: {job.get('title')}")
                                skipped_count += 1
                                job['saved'] = False
                                job['reason'] = '已存在'
                                continue
                        
                        # 构建完整描述
                        full_desc = job.get('job_description', '')
                        if not full_desc:
                            full_desc = f"{job.get('title', '')}\n公司：{job.get('company', '')}\n薪资：{job.get('salary', '')}"
                        
                        # 提取结构化数据
                        structured_data, confidence, method = extractor.extract_job(
                            text=full_desc,
                            use_llm=False,
                            force_llm=False
                        )
                        
                        # 补充基本信息
                        structured_data['title'] = job.get('title', '')
                        structured_data['company'] = job.get('company', '')
                        structured_data['company_name'] = job.get('company_name', '')
                        structured_data['salary_range'] = job.get('salary_detail', job.get('salary', ''))
                        structured_data['job_keywords'] = job.get('job_keywords', [])
                        
                        # 生成向量
                        try:
                            embedding = embedding_service.create_embedding(full_desc[:1000])
                        except:
                            embedding = None
                        
                        # 保存
                        job_record = JobV2(
                            external_id=job_id,
                            platform="boss",
                            job_url=job.get('job_url', ''),
                            title=job.get('title', ''),
                            company_name=job.get('company_name', job.get('company', '')),
                            city=job.get('work_city', request.city),
                            salary_text=job.get('salary_detail', job.get('salary', '')),
                            experience_required=job.get('experience_requirement', job.get('experience', '')),
                            education_required=job.get('education_requirement', job.get('education', '')),
                            full_description=full_desc,
                            structured_data=structured_data,
                            extraction_method=method,
                            extraction_confidence=confidence,
                            description_embedding=embedding,
                            is_active=True
                        )
                        
                        db.add(job_record)
                        await db.commit()
                        await db.refresh(job_record)
                        
                        saved_count += 1
                        job['saved'] = True
                        job['db_id'] = job_record.id
                        logger.info(f"✅ 职位保存成功: {job.get('title')} (ID={job_record.id})")
                    
                    except Exception as e:
                        logger.error(f"❌ 保存职位失败: {e}")
                        failed_count += 1
                        job['saved'] = False
                        job['reason'] = str(e)
            
            return CrawlResponse(
                total_found=len(all_jobs),
                saved_count=saved_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                jobs=jobs
            )
        
        except Exception as e:
            logger.error(f"❌ 爬取失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/boss/test")
async def test_boss_crawler():
    """
    测试BOSS直聘爬虫（不保存数据库）
    
    Returns:
        测试结果
    """
    logger.info("🧪 测试BOSS直聘Playwright爬虫...")
    
    if not settings.BOSS_COOKIE:
        return {
            "success": False,
            "message": "未配置Cookie，请通过环境变量BOSS_COOKIE设置",
            "jobs": [],
            "stats": {}
        }
    
    async with BossWebCrawlerPlaywright(
        min_delay=1.5,
        max_delay=3.0,
        headless=True,
        cookie_string=settings.BOSS_COOKIE,
        target_city="深圳"
    ) as crawler:
        try:
            # 测试搜索（只爬3个职位）
            jobs = await crawler.search_jobs(
                keyword="Python",
                city="深圳",
                page=1,
                auto_scroll=False
            )
            
            if not jobs:
                return {
                    "success": False,
                    "message": "未找到任何职位",
                    "jobs": [],
                    "stats": crawler.get_stats()
                }
            
            # 获取前3个的详情
            jobs = jobs[:3]
            for job in jobs:
                job_url = job.get('job_url')
                if job_url:
                    detail = await crawler.get_job_detail(job_url, use_random_ua=True)
                    if detail:
                        job.update(detail)
            
            return {
                "success": True,
                "message": f"✅ 测试成功，找到 {len(jobs)} 个职位",
                "jobs": jobs,
                "stats": crawler.get_stats()
            }
        
        except Exception as e:
            logger.error(f"❌ 测试失败: {e}")
            return {
                "success": False,
                "message": f"测试失败: {str(e)}",
                "jobs": [],
                "stats": crawler.get_stats()
            }


@router.get("/cities")
async def get_supported_cities():
    """
    获取支持的城市列表
    
    Returns:
        支持的城市及其代码
    """
    return {
        "cities": BossWebCrawlerPlaywright.CITY_CODES
    }
