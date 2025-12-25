"""
DeepCareer 主程序
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.config import settings
from backend.database import init_db, close_db
from backend.services import cache_service
from backend.api import resume, search, feedback, analytics, crawler
from backend.api import resume_v2, job_v2, match_v2, smart_match
from backend.utils.logger import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 50)
    logger.info("DeepCareer 正在启动...")
    logger.info("=" * 50)
    
    # 初始化日志
    setup_logger()
    
    # 连接 Redis
    try:
        await cache_service.connect()
    except Exception as e:
        logger.warning(f"Redis 连接失败（将在无缓存模式下运行）: {str(e)}")
    
    # 初始化数据库
    try:
        await init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise
    
    logger.info("DeepCareer 启动成功！")
    logger.info(f"服务地址: http://{settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"API 文档: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    
    yield
    
    # 关闭时执行
    logger.info("DeepCareer 正在关闭...")
    
    await cache_service.close()
    await close_db()
    
    logger.info("DeepCareer 已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="DeepCareer API",
    description="智能职位推荐系统 - 基于 AI 的简历分析与职位匹配",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
# V1 路由
app.include_router(resume.router)
app.include_router(search.router)
app.include_router(feedback.router)
app.include_router(analytics.router)

# V2 路由（新版本）
app.include_router(resume_v2.router)
app.include_router(job_v2.router)
app.include_router(match_v2.router)
app.include_router(smart_match.router)

# 爬虫路由
app.include_router(crawler.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to DeepCareer API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "DeepCareer",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
