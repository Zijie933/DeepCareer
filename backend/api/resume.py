"""
简历相关 API
"""
import os
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.database import get_db
from backend.models.resume_v2 import ResumeV2 as Resume
from backend.schemas.resume import (
    ResumeUploadResponse,
    ResumeParseResponse,
    ResumeDetailResponse,
)
from backend.services.resume_parser import resume_parser
from backend.services.openai_service import openai_service
from backend.agents.resume_analyzer import resume_analyzer
from backend.config import settings

router = APIRouter(prefix="/api/resume", tags=["简历"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    上传简历文件
    
    支持格式：PDF, DOCX, PNG, JPG, JPEG
    """
    # 验证文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
        )
    
    # 验证文件大小
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到开头
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大。最大允许 {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB"
        )
    
    try:
        # 创建上传目录
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        timestamp = int(time.time() * 1000)
        file_name = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, file_name)
        
        # 保存文件
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 创建数据库记录
        resume = Resume(
            user_id=user_id,
            file_name=file.filename,
            file_path=file_path,
            file_type=file_ext[1:],  # 去掉点号
        )
        
        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        
        logger.info(f"简历上传成功 - ID: {resume.id}, 文件: {file.filename}")
        
        return ResumeUploadResponse(
            success=True,
            resume_id=resume.id,
            file_name=file.filename,
            message="简历上传成功",
        )
    
    except Exception as e:
        logger.error(f"简历上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/parse/{resume_id}", response_model=ResumeParseResponse)
async def parse_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    解析简历并进行深度分析
    """
    # 获取简历记录
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="简历文件不存在")
    
    try:
        # 1. 解析文件提取文本
        parse_result = await resume_parser.parse_file(resume.file_path)
        
        if not parse_result["success"]:
            raise HTTPException(status_code=400, detail=parse_result["error"])
        
        full_text = parse_result["text"]
        
        # 2. 使用 ResumeAnalyzer 深度分析
        analysis_result = await resume_analyzer.analyze(full_text)
        
        # 3. 评估简历质量
        quality_assessment = await resume_analyzer.assess_quality(full_text)
        quality_score = quality_assessment.get("score", 0)
        
        # 4. 生成向量
        text_embedding = await openai_service.create_embedding(full_text)
        
        # 5. 更新数据库
        resume.full_text = full_text
        resume.parsed_data = analysis_result
        resume.analysis_result = analysis_result
        resume.quality_score = quality_score
        resume.text_embedding = text_embedding
        
        await db.commit()
        
        logger.info(f"简历解析成功 - ID: {resume_id}, 质量分: {quality_score}")
        
        return ResumeParseResponse(
            success=True,
            resume_id=resume_id,
            full_text=full_text,
            parsed_data=analysis_result,
            analysis_result=analysis_result,
            quality_score=quality_score,
            message="简历解析成功",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"简历解析失败 (resume_id={resume_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取简历详情
    """
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    return ResumeDetailResponse.from_orm(resume)
