"""
简历API V2 - 支持规则提取和大模型提取
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import os

from backend.database.connection import get_db
from backend.models.resume_v2 import ResumeV2
from backend.services.extractor_service import ExtractorService
from backend.services.resume_parser import ResumeParser
from backend.utils.local_embedding import LocalEmbeddingService
from backend.utils.logger import logger

router = APIRouter(prefix="/api/v2/resumes", tags=["简历V2"])

extractor = ExtractorService()
embedding_service = LocalEmbeddingService()


async def extract_text_from_file(file_path: str, file_type: str) -> str:
    """从文件中提取文本，使用增强的解析器"""
    result = await ResumeParser.parse_file(file_path)
    
    if not result["success"]:
        raise ValueError(f"文件解析失败: {result['error']}")
    
    return result["text"]


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    use_llm: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """
    上传简历并自动提取结构化数据
    
    Args:
        file: 简历文件（支持PDF/DOCX/TXT）
        user_id: 用户ID（可选）
        use_llm: 是否允许使用大模型提取（默认False，只用规则）
    
    Returns:
        {
            "id": 简历ID,
            "structured_data": 结构化数据,
            "extraction_method": "rule" 或 "llm",
            "extraction_confidence": 置信度,
            "message": "请在表单中确认或补充信息"
        }
    """
    logger.info(f"收到简历上传: {file.filename}, use_llm={use_llm}")
    
    # 1. 保存文件
    upload_dir = "uploads/resumes"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_type = file.filename.split('.')[-1].lower()
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)
    
    # 2. 提取文本
    try:
        full_text = await extract_text_from_file(file_path, file_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")
    
    # 3. 智能提取结构化数据
    structured_data, confidence, method = extractor.extract_resume(
        text=full_text,
        use_llm=use_llm,
        force_llm=False
    )
    
    # 4. 生成向量（异步）
    try:
        embedding = embedding_service.create_embedding(full_text[:1000])  # 取前1000字
    except Exception as e:
        logger.warning(f"向量生成失败: {e}")
        embedding = None
    
    # 5. 保存到数据库
    resume = ResumeV2(
        user_id=user_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file_type,
        full_text=full_text,
        structured_data=structured_data,
        extraction_method=method,
        extraction_confidence=confidence,
        text_embedding=embedding,
        user_confirmed=False  # 待用户确认
    )
    
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    
    logger.info(f"简历保存成功: ID={resume.id}, method={method}, confidence={confidence:.2f}")
    
    return {
        "id": resume.id,
        "structured_data": structured_data,
        "extraction_method": method,
        "extraction_confidence": round(confidence, 2),
        "message": "简历已解析，请在表单中确认或补充信息" if confidence < 0.9 else "简历解析完成"
    }


@router.put("/{resume_id}/confirm")
async def confirm_resume(
    resume_id: int,
    structured_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    用户确认/修改结构化数据
    
    Args:
        resume_id: 简历ID
        structured_data: 用户确认后的结构化数据
    """
    result = await db.execute(select(ResumeV2).where(ResumeV2.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    # 更新数据
    resume.structured_data = structured_data
    resume.user_confirmed = True
    
    # 重新生成向量（如果文本有变化）
    try:
        # 将结构化数据转为文本
        text_parts = []
        for key, value in structured_data.items():
            if isinstance(value, list):
                text_parts.append(' '.join(str(v) for v in value))
            elif value:
                text_parts.append(str(value))
        
        combined_text = ' '.join(text_parts)
        resume.text_embedding = embedding_service.create_embedding(combined_text)
    except Exception as e:
        logger.warning(f"向量更新失败: {e}")
    
    await db.commit()
    
    logger.info(f"简历{resume_id}已确认")
    return {"message": "简历信息已确认", "id": resume_id}


@router.post("/{resume_id}/extract-with-llm")
async def extract_with_llm(
    resume_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    使用大模型重新提取（如果规则提取不满意）
    
    Args:
        resume_id: 简历ID
    """
    result = await db.execute(select(ResumeV2).where(ResumeV2.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    if not resume.full_text:
        raise HTTPException(status_code=400, detail="简历无原文，无法重新提取")
    
    # 强制使用大模型
    structured_data, confidence, method = extractor.extract_resume(
        text=resume.full_text,
        use_llm=True,
        force_llm=True
    )
    
    # 更新
    resume.structured_data = structured_data
    resume.extraction_method = method
    resume.extraction_confidence = confidence
    resume.user_confirmed = False  # 需要重新确认
    
    await db.commit()
    
    logger.info(f"简历{resume_id}已使用大模型重新提取")
    return {
        "id": resume_id,
        "structured_data": structured_data,
        "extraction_method": method,
        "extraction_confidence": round(confidence, 2),
        "message": "大模型提取完成，请确认数据"
    }


@router.get("/{resume_id}")
async def get_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    """获取简历详情"""
    result = await db.execute(select(ResumeV2).where(ResumeV2.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    return resume.to_dict()


@router.get("/")
async def list_resumes(
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取简历列表"""
    # 构建查询
    query = select(ResumeV2)
    count_query = select(func.count()).select_from(ResumeV2)
    
    if user_id:
        query = query.where(ResumeV2.user_id == user_id)
        count_query = count_query.where(ResumeV2.user_id == user_id)
    
    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 获取数据
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    resumes = result.scalars().all()
    
    return {
        "total": total,
        "items": [r.to_dict() for r in resumes]
    }
