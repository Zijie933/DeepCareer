"""
智能匹配API - 选择简历自动匹配岗位
流程：
1. 用户选择已上传的简历
2. 从简历提取搜索关键词（职位、技能等）
3. 先从数据库匹配岗位（立即返回第一批结果）
4. 如果不足10个，触发爬虫搜索（支持多关键词）
5. 爬虫结果保存/更新到数据库（upsert）
6. 流式返回匹配结果
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import Optional, List
from pydantic import BaseModel
import asyncio
import json

from backend.database.connection import get_db, async_session_factory
from backend.models.resume_v2 import ResumeV2
from backend.models.job_v2 import JobV2
from backend.models.match_record import MatchRecord
from backend.services.matcher_service import MatcherService
from backend.services.extractor_service import ExtractorService
from backend.crawlers.boss_web_crawler_playwright import BossWebCrawlerPlaywright
from backend.utils.local_embedding import LocalEmbeddingService
from backend.utils.logger import logger
from backend.config import settings

router = APIRouter(prefix="/api/v2/smart-match", tags=["智能匹配"])

matcher = MatcherService()
extractor = ExtractorService()
embedding_service = LocalEmbeddingService()


class SmartMatchRequest(BaseModel):
    """智能匹配请求"""
    resume_id: int  # 简历ID
    min_jobs: int = 10  # 最少匹配岗位数（指60%以上的）
    max_jobs: int = 20  # 最多返回岗位数
    city: Optional[str] = None  # 指定城市（可选，默认从简历提取）
    extra_keywords: Optional[List[str]] = None  # 额外搜索关键词
    enable_crawler: bool = True  # 是否启用爬虫补充
    qualified_threshold: float = 60.0  # 合格匹配分数阈值（默认60%）
    min_display_score: float = 30.0  # 最低展示分数（低于此分数不展示）


class SmartMatchResponse(BaseModel):
    """智能匹配响应"""
    resume_id: int
    resume_name: str
    search_keywords: List[str]  # 使用的搜索关键词
    target_city: str  # 目标城市
    total_matched: int  # 总匹配数
    qualified_count: int  # 合格数量（>=60%）
    from_database: int  # 来自数据库的数量
    from_crawler: int  # 来自爬虫的数量
    matches: List[dict]  # 匹配结果（按分数排序，包含合格和不合格）


def extract_search_keywords(resume_data: dict) -> List[str]:
    """
    从简历数据提取搜索关键词
    
    优先级：
    1. 当前职位
    2. 求职意向职位
    3. 核心技能
    """
    keywords = []
    
    # 1. 当前职位
    current_position = resume_data.get('current_position')
    if current_position:
        # 清理职位名称
        position = current_position.replace('高级', '').replace('资深', '').replace('初级', '').strip()
        if position and len(position) >= 2:
            keywords.append(position)
    
    # 2. 求职意向
    job_intention = resume_data.get('job_intention', {})
    if job_intention:
        positions = job_intention.get('positions', [])
        for pos in positions[:2]:  # 最多取2个
            if pos and pos not in keywords:
                keywords.append(pos)
    
    # 3. 核心技能（选择热门技能）
    skills = resume_data.get('skills', {})
    hot_skills = []
    
    if isinstance(skills, dict):
        # 分类技能
        for category in ['programming_languages', 'frameworks']:
            category_skills = skills.get(category, [])
            hot_skills.extend(category_skills[:2])
    elif isinstance(skills, list):
        hot_skills = skills[:3]
    
    # 组合技能关键词
    for skill in hot_skills[:3]:
        if skill and skill not in keywords:
            # 技能通常需要组合搜索，如 "Python开发"
            keywords.append(skill)
    
    # 4. 如果还没有关键词，使用通用关键词
    if not keywords:
        keywords = ['开发工程师', 'Python', 'Java']
    
    return keywords[:5]  # 最多5个关键词


async def crawl_jobs_for_keywords(
    keywords: List[str],
    city: str,
    max_per_keyword: int,
    db: AsyncSession
) -> List[dict]:
    """
    根据多个关键词爬取职位（快速版，不滚动）
    
    Args:
        keywords: 搜索关键词列表
        city: 城市
        max_per_keyword: 每个关键词最多爬取数量
        db: 数据库会话
    
    Returns:
        爬取并保存的职位列表
    """
    if not settings.BOSS_COOKIE:
        logger.warning("未配置BOSS_COOKIE，跳过爬虫")
        return []
    
    logger.info(f"🍪 BOSS_COOKIE已配置，长度: {len(settings.BOSS_COOKIE)} 字符")
    logger.info(f"🔧 爬虫参数: keywords={keywords}, city={city}, max_per_keyword={max_per_keyword}")
    
    all_jobs = []
    seen_job_ids = set()
    
    async with BossWebCrawlerPlaywright(
        min_delay=1.0,
        max_delay=2.0,
        headless=True,
        cookie_string=settings.BOSS_COOKIE,
        target_city=city
    ) as crawler:
        for keyword in keywords:
            try:
                logger.info(f"🔍 爬取关键词: {keyword}, 城市: {city}")
                
                # 快速搜索职位（不滚动，只取首屏，速度优先）
                jobs = await crawler.search_jobs(
                    keyword=keyword,
                    city=city,
                    page=1,
                    auto_scroll=False,  # 不滚动，快速返回
                    max_scroll=0
                )
                
                if not jobs:
                    logger.warning(f"关键词 '{keyword}' 未找到职位")
                    continue
                
                # 限制数量并去重
                for job in jobs[:max_per_keyword]:
                    job_id = job.get('job_id', '')
                    if job_id and job_id not in seen_job_ids:
                        seen_job_ids.add(job_id)
                        job['search_keyword'] = keyword
                        all_jobs.append(job)
                
                logger.info(f"✅ 关键词 '{keyword}' 找到 {len(jobs)} 个职位")
                
            except Exception as e:
                logger.error(f"❌ 爬取关键词 '{keyword}' 失败: {e}")
                continue
    
    # 获取详情并保存到数据库
    saved_jobs = []
    
    for job in all_jobs:
        try:
            job_id = job.get('job_id', '')
            
            # 检查是否已存在
            result = await db.execute(
                select(JobV2).where(JobV2.external_id == job_id)
            )
            existing = result.scalar_one_or_none()
            
            # 构建描述
            full_desc = job.get('job_description', '')
            if not full_desc:
                full_desc = f"{job.get('title', '')}\n公司：{job.get('company', '')}\n薪资：{job.get('salary', '')}"
            
            # 提取结构化数据
            structured_data, confidence, method = extractor.extract_job(
                text=full_desc,
                use_llm=False
            )
            
            # 补充信息
            structured_data['title'] = job.get('title', '')
            structured_data['company'] = job.get('company', '')
            structured_data['salary_range'] = job.get('salary', '')
            structured_data['job_keywords'] = job.get('job_keywords', [])
            
            # 生成向量
            try:
                embedding = embedding_service.create_embedding(full_desc[:1000])
            except:
                embedding = None
            
            if existing:
                # 更新已存在的职位
                await db.execute(
                    update(JobV2).where(JobV2.id == existing.id).values(
                        title=job.get('title', existing.title),
                        company_name=job.get('company_name', job.get('company', existing.company_name)),
                        salary_text=job.get('salary', existing.salary_text),
                        full_description=full_desc if full_desc else existing.full_description,
                        structured_data=structured_data,
                        description_embedding=embedding if embedding else existing.description_embedding,
                        is_active=True
                    )
                )
                await db.commit()
                
                # 刷新获取最新数据
                await db.refresh(existing)
                saved_jobs.append({
                    'id': existing.id,
                    'title': existing.title,
                    'company_name': existing.company_name,
                    'city': existing.city,
                    'salary_text': existing.salary_text,
                    'job_url': existing.job_url,
                    'from_crawler': True,
                    'updated': True
                })
                logger.info(f"🔄 更新职位: {job.get('title')} (ID={existing.id})")
            else:
                # 创建新职位
                job_record = JobV2(
                    external_id=job_id,
                    platform="boss",
                    job_url=job.get('job_url', ''),
                    title=job.get('title', ''),
                    company_name=job.get('company_name', job.get('company', '')),
                    city=job.get('work_city', city),
                    salary_text=job.get('salary', ''),
                    experience_required=job.get('experience', ''),
                    education_required=job.get('education', ''),
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
                
                saved_jobs.append({
                    'id': job_record.id,
                    'title': job_record.title,
                    'company_name': job_record.company_name,
                    'city': job_record.city,
                    'salary_text': job_record.salary_text,
                    'job_url': job_record.job_url,
                    'from_crawler': True,
                    'updated': False
                })
                logger.info(f"✅ 新增职位: {job.get('title')} (ID={job_record.id})")
        
        except Exception as e:
            logger.error(f"❌ 保存职位失败: {e}")
            continue
    
    return saved_jobs


@router.post("/stream")
async def smart_match_stream(
    request: SmartMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    流式智能匹配岗位（SSE）
    
    流程：
    1. 立即返回数据库匹配结果（第一批）
    2. 前端显示"正在获取更多职位..."
    3. 后台爬虫搜索，实时推送新结果
    4. 完成后发送结束信号
    
    SSE 事件类型：
    - db_matches: 数据库匹配结果
    - crawling: 爬虫进度
    - crawler_matches: 爬虫匹配结果
    - complete: 完成
    - error: 错误
    """
    
    async def generate_matches():
        try:
            # 1. 获取简历
            result = await db.execute(select(ResumeV2).where(ResumeV2.id == request.resume_id))
            resume = result.scalar_one_or_none()
            if not resume:
                yield f"data: {json.dumps({'type': 'error', 'message': '简历不存在'})}\n\n"
                return
            
            resume_data = resume.structured_data or {}
            resume_name = resume_data.get('name', '未知')
            
            # 2. 提取搜索关键词
            keywords = extract_search_keywords(resume_data)
            if request.extra_keywords:
                keywords.extend(request.extra_keywords)
            keywords = list(set(keywords))[:5]
            
            # 3. 确定城市
            city = request.city
            if not city:
                city = resume_data.get('location')
                if not city:
                    job_intention = resume_data.get('job_intention', {})
                    cities = job_intention.get('cities', [])
                    city = cities[0] if cities else '深圳'
            city = city.replace('市', '').strip()
            
            logger.info(f"🚀 流式匹配开始: resume_id={request.resume_id}, city={city}")
            
            # 4. 从数据库查询同城市的职位
            db_jobs_result = await db.execute(
                select(JobV2).where(
                    JobV2.is_active == True,
                    JobV2.city.ilike(f"%{city}%")
                ).limit(200)
            )
            db_jobs = db_jobs_result.scalars().all()
            
            # 5. 计算匹配分数
            qualified_matches = []
            unqualified_matches = []
            
            for job in db_jobs:
                try:
                    score, details = matcher.fast_match(
                        resume_data=resume_data,
                        job_data=job.structured_data or {},
                        resume_embedding=resume.text_embedding,
                        job_embedding=job.description_embedding
                    )
                    
                    if score < request.min_display_score:
                        continue
                    
                    match_item = {
                        'job_id': job.id,
                        'title': job.title,
                        'company_name': job.company_name,
                        'city': job.city,
                        'salary_text': job.salary_text,
                        'job_url': job.job_url,
                        'experience_required': job.experience_required,
                        'education_required': job.education_required,
                        'match_score': round(score, 2),
                        'match_details': details,
                        'is_qualified': score >= request.qualified_threshold,
                        'from_database': True,
                        'from_crawler': False
                    }
                    
                    if score >= request.qualified_threshold:
                        qualified_matches.append(match_item)
                    else:
                        unqualified_matches.append(match_item)
                except Exception as e:
                    logger.error(f"匹配职位 {job.id} 失败: {e}")
                    continue
            
            # 排序
            qualified_matches.sort(key=lambda x: x['match_score'], reverse=True)
            unqualified_matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            all_db_matches = qualified_matches + unqualified_matches
            qualified_count = len(qualified_matches)
            
            logger.info(f"📊 数据库匹配完成: 合格{qualified_count}个, 不合格{len(unqualified_matches)}个")
            
            # 6. 立即发送数据库匹配结果
            yield f"data: {json.dumps({'type': 'db_matches', 'data': {'resume_id': resume.id, 'resume_name': resume_name, 'target_city': city, 'search_keywords': keywords, 'matches': all_db_matches, 'qualified_count': qualified_count, 'from_database': len(all_db_matches), 'from_crawler': 0, 'need_crawler': request.enable_crawler and qualified_count < request.min_jobs}}, ensure_ascii=False)}\n\n"
            
            # 7. 如果合格数量不足，启动爬虫
            if request.enable_crawler and qualified_count < request.min_jobs:
                needed = request.min_jobs - qualified_count
                
                yield f"data: {json.dumps({'type': 'crawling', 'message': f'合格职位不足，正在搜索更多职位...', 'needed': needed}, ensure_ascii=False)}\n\n"
                
                # 爬虫搜索（使用新的数据库会话）
                crawler_matches = []
                existing_job_ids = [m['job_id'] for m in all_db_matches]
                
                try:
                    async with async_session_factory() as crawler_db:
                        crawled_jobs = await crawl_jobs_for_keywords(
                            keywords=keywords,
                            city=city,
                            max_per_keyword=max(5, needed // len(keywords) + 1),
                            db=crawler_db
                        )
                        
                        # 对爬取的职位计算匹配分数
                        for crawled in crawled_jobs:
                            if crawled['id'] in existing_job_ids:
                                continue
                            
                            job_result = await crawler_db.execute(
                                select(JobV2).where(JobV2.id == crawled['id'])
                            )
                            job = job_result.scalar_one_or_none()
                            
                            if job:
                                try:
                                    score, details = matcher.fast_match(
                                        resume_data=resume_data,
                                        job_data=job.structured_data or {},
                                        resume_embedding=resume.text_embedding,
                                        job_embedding=job.description_embedding
                                    )
                                    
                                    if score < request.min_display_score:
                                        continue
                                    
                                    match_item = {
                                        'job_id': job.id,
                                        'title': job.title,
                                        'company_name': job.company_name,
                                        'city': job.city,
                                        'salary_text': job.salary_text,
                                        'job_url': job.job_url,
                                        'experience_required': job.experience_required,
                                        'education_required': job.education_required,
                                        'match_score': round(score, 2),
                                        'match_details': details,
                                        'is_qualified': score >= request.qualified_threshold,
                                        'from_database': False,
                                        'from_crawler': True
                                    }
                                    
                                    crawler_matches.append(match_item)
                                    existing_job_ids.append(job.id)
                                    
                                    # 每找到一个新职位就推送
                                    yield f"data: {json.dumps({'type': 'crawler_match', 'data': match_item}, ensure_ascii=False)}\n\n"
                                    
                                except Exception as e:
                                    logger.error(f"匹配爬取职位失败: {e}")
                                    continue
                    
                    logger.info(f"🕷️ 爬虫完成: 新增{len(crawler_matches)}个匹配")
                    
                except Exception as e:
                    logger.error(f"❌ 爬虫失败: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'爬虫搜索失败: {str(e)}'}, ensure_ascii=False)}\n\n"
            
            # 8. 发送完成信号
            final_qualified = qualified_count + sum(1 for m in crawler_matches if m.get('is_qualified', False)) if 'crawler_matches' in dir() else qualified_count
            yield f"data: {json.dumps({'type': 'complete', 'message': '匹配完成', 'total_qualified': final_qualified}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"流式匹配错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_matches(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/", response_model=SmartMatchResponse)
async def smart_match(
    request: SmartMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    智能匹配岗位（非流式，等待全部完成）
    
    流程：
    1. 获取简历并提取搜索关键词
    2. 确定目标城市
    3. 从数据库查询【同城市】的职位（地区筛选优先）
    4. 计算匹配分数，区分合格（>=60%）和不合格
    5. 如果合格数量不足min_jobs，触发爬虫搜索
    6. 返回匹配结果（合格的在前，不合格的在后）
    
    Args:
        request: 智能匹配请求
    
    Returns:
        匹配结果
    """
    logger.info(f"🚀 开始智能匹配: resume_id={request.resume_id}")
    
    # 1. 获取简历
    result = await db.execute(select(ResumeV2).where(ResumeV2.id == request.resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    resume_data = resume.structured_data or {}
    resume_name = resume_data.get('name', '未知')
    
    # 2. 提取搜索关键词
    keywords = extract_search_keywords(resume_data)
    if request.extra_keywords:
        keywords.extend(request.extra_keywords)
    keywords = list(set(keywords))[:5]  # 去重，最多5个
    
    logger.info(f"📝 搜索关键词: {keywords}")
    
    # 3. 确定城市（地区筛选优先）
    city = request.city
    if not city:
        # 从简历提取
        city = resume_data.get('location')
        if not city:
            job_intention = resume_data.get('job_intention', {})
            cities = job_intention.get('cities', [])
            city = cities[0] if cities else '深圳'
    
    # 标准化城市名称（去除"市"后缀）
    city = city.replace('市', '').strip()
    
    logger.info(f"📍 目标城市: {city}（地区筛选优先）")
    
    # 4. 从数据库查询【同城市】的职位（地区筛选优先！）
    db_jobs_result = await db.execute(
        select(JobV2).where(
            JobV2.is_active == True,
            # 地区筛选：城市必须匹配
            JobV2.city.ilike(f"%{city}%")
        ).limit(200)
    )
    db_jobs = db_jobs_result.scalars().all()
    
    logger.info(f"📊 数据库中【{city}】有 {len(db_jobs)} 个活跃职位")
    
    # 5. 计算匹配分数
    qualified_matches = []  # 合格的（>=60%）
    unqualified_matches = []  # 不合格的（<60%但>=min_display_score）
    
    for job in db_jobs:
        try:
            score, details = matcher.fast_match(
                resume_data=resume_data,
                job_data=job.structured_data or {},
                resume_embedding=resume.text_embedding,
                job_embedding=job.description_embedding
            )
            
            # 低于最低展示分数的直接跳过
            if score < request.min_display_score:
                continue
            
            match_item = {
                'job_id': job.id,
                'title': job.title,
                'company_name': job.company_name,
                'city': job.city,
                'salary_text': job.salary_text,
                'job_url': job.job_url,
                'experience_required': job.experience_required,
                'education_required': job.education_required,
                'match_score': round(score, 2),
                'match_details': details,
                'is_qualified': score >= request.qualified_threshold,  # 是否合格
                'from_database': True,
                'from_crawler': False
            }
            
            if score >= request.qualified_threshold:
                qualified_matches.append(match_item)
            else:
                unqualified_matches.append(match_item)
                
        except Exception as e:
            logger.error(f"匹配职位 {job.id} 失败: {e}")
            continue
    
    # 排序
    qualified_matches.sort(key=lambda x: x['match_score'], reverse=True)
    unqualified_matches.sort(key=lambda x: x['match_score'], reverse=True)
    
    from_database_count = len(qualified_matches) + len(unqualified_matches)
    qualified_count = len(qualified_matches)
    
    logger.info(f"✅ 数据库匹配: 合格({qualified_count}个, >={request.qualified_threshold}%), 不合格({len(unqualified_matches)}个)")
    
    # 6. 如果合格数量不足，触发爬虫
    from_crawler_count = 0
    if request.enable_crawler and qualified_count < request.min_jobs:
        needed = request.min_jobs - qualified_count
        max_per_keyword = max(5, needed // len(keywords) + 1)
        
        logger.info(f"🕷️ 合格职位不足({qualified_count}<{request.min_jobs})，启动爬虫补充（需要 {needed} 个）")
        
        try:
            crawled_jobs = await crawl_jobs_for_keywords(
                keywords=keywords,
                city=city,
                max_per_keyword=max_per_keyword,
                db=db
            )
            
            # 对爬取的职位计算匹配分数
            for crawled in crawled_jobs:
                # 检查是否已在匹配列表中
                all_job_ids = [m['job_id'] for m in qualified_matches + unqualified_matches]
                if crawled['id'] in all_job_ids:
                    continue
                
                # 获取完整职位信息
                job_result = await db.execute(
                    select(JobV2).where(JobV2.id == crawled['id'])
                )
                job = job_result.scalar_one_or_none()
                
                if job:
                    try:
                        score, details = matcher.fast_match(
                            resume_data=resume_data,
                            job_data=job.structured_data or {},
                            resume_embedding=resume.text_embedding,
                            job_embedding=job.description_embedding
                        )
                        
                        if score < request.min_display_score:
                            continue
                        
                        match_item = {
                            'job_id': job.id,
                            'title': job.title,
                            'company_name': job.company_name,
                            'city': job.city,
                            'salary_text': job.salary_text,
                            'job_url': job.job_url,
                            'experience_required': job.experience_required,
                            'education_required': job.education_required,
                            'match_score': round(score, 2),
                            'match_details': details,
                            'is_qualified': score >= request.qualified_threshold,
                            'from_database': False,
                            'from_crawler': True
                        }
                        
                        if score >= request.qualified_threshold:
                            qualified_matches.append(match_item)
                        else:
                            unqualified_matches.append(match_item)
                        
                        from_crawler_count += 1
                    except Exception as e:
                        logger.error(f"匹配爬取职位失败: {e}")
                        continue
            
            # 重新排序
            qualified_matches.sort(key=lambda x: x['match_score'], reverse=True)
            unqualified_matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            logger.info(f"🕷️ 爬虫补充了 {from_crawler_count} 个匹配职位")
        
        except Exception as e:
            logger.error(f"❌ 爬虫失败: {e}")
    
    # 7. 合并结果：合格的在前，不合格的在后
    all_matches = qualified_matches + unqualified_matches
    
    # 限制总数量
    final_matches = all_matches[:request.max_jobs]
    final_qualified_count = sum(1 for m in final_matches if m['is_qualified'])
    
    # 8. 保存匹配记录
    for match in final_matches:
        try:
            # 检查是否已有记录
            existing = await db.execute(
                select(MatchRecord).where(
                    MatchRecord.resume_id == resume.id,
                    MatchRecord.job_id == match['job_id'],
                    MatchRecord.match_method == 'fast'
                )
            )
            if not existing.scalar_one_or_none():
                record = MatchRecord(
                    resume_id=resume.id,
                    job_id=match['job_id'],
                    match_method='fast',
                    fast_score=match['match_score'],
                    fast_details=match['match_details']
                )
                db.add(record)
        except:
            pass
    
    await db.commit()
    
    logger.info(f"🎉 智能匹配完成: 共 {len(final_matches)} 个结果, 合格 {final_qualified_count} 个")
    
    return SmartMatchResponse(
        resume_id=resume.id,
        resume_name=resume_name,
        search_keywords=keywords,
        target_city=city,
        total_matched=len(final_matches),
        qualified_count=final_qualified_count,
        from_database=from_database_count,
        from_crawler=from_crawler_count,
        matches=final_matches
    )


@router.get("/resumes")
async def list_resumes_for_match(
    db: AsyncSession = Depends(get_db)
):
    """
    获取可用于匹配的简历列表（包含完整结构化数据用于预览）
    """
    result = await db.execute(
        select(ResumeV2).order_by(ResumeV2.created_at.desc())
    )
    resumes = result.scalars().all()
    
    items = []
    for r in resumes:
        data = r.structured_data or {}
        
        # 提取技能列表
        skills = []
        skills_data = data.get('skills', {})
        if isinstance(skills_data, dict):
            for category in ['programming_languages', 'frameworks', 'tools', 'databases', 'other']:
                skills.extend(skills_data.get(category, []))
        elif isinstance(skills_data, list):
            skills = skills_data
        
        items.append({
            "id": r.id,
            "name": data.get('name', '未知'),
            "email": data.get('email'),
            "phone": data.get('phone'),
            "current_position": data.get('current_position'),
            "years_experience": data.get('years_experience'),
            "education": data.get('education'),
            "location": data.get('location'),
            "file_name": r.file_name,
            "extraction_method": r.extraction_method,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            # 完整结构化数据用于预览
            "structured_data": data,
            # 扁平化的技能列表方便展示
            "skills": skills[:15]
        })
    
    return {
        "total": len(resumes),
        "items": items
    }


@router.get("/keywords/{resume_id}")
async def get_resume_keywords(
    resume_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取简历的推荐搜索关键词
    """
    result = await db.execute(select(ResumeV2).where(ResumeV2.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    keywords = extract_search_keywords(resume.structured_data or {})
    
    # 获取简历中的城市
    resume_data = resume.structured_data or {}
    city = resume_data.get('location')
    if not city:
        job_intention = resume_data.get('job_intention', {})
        cities = job_intention.get('cities', [])
        city = cities[0] if cities else None
    
    return {
        "resume_id": resume_id,
        "name": resume_data.get('name', '未知'),
        "keywords": keywords,
        "suggested_city": city,
        "available_cities": list(BossWebCrawlerPlaywright.CITY_CODES.keys())
    }
