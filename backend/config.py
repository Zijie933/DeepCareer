"""
DeepCareer 配置管理模块
支持从环境变量和 .env 文件加载配置
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    
    # ========== OpenAI 配置 ==========
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"  # API 基础 URL（支持代理）
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_TIMEOUT: int = 60
    
    # ========== 本地 Embedding 配置 ==========
    USE_LOCAL_EMBEDDING: bool = True  # 是否使用本地Embedding
    LOCAL_EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"  # 本地模型名(384维)
    
    # ========== 数据库配置 ==========
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "deepcareer"
    POSTGRES_USER: str = "deepcareer_user"
    POSTGRES_PASSWORD: str
    
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False
    
    @property
    def DATABASE_URL(self) -> str:
        """生成数据库连接 URL"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """生成同步数据库连接 URL（用于 Alembic）"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ========== Redis 配置 ==========
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    CACHE_EXPIRE_TIME: int = 3600  # 1小时
    
    @property
    def REDIS_URL(self) -> str:
        """生成 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ========== 应用配置 ==========
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    
    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """解析 CORS origins"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # 文件上传
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "./uploads"
    
    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/deepcareer.log"
    
    # ========== 爬虫配置 ==========
    BOSS_COOKIE: str = ""  # BOSS直聘Cookie，可通过环境变量BOSS_COOKIE设置
    
    # ========== 向量搜索配置 ==========
    EMBEDDING_DIMENSION: int = 384  # paraphrase-multilingual-MiniLM-L12-v2
    VECTOR_SEARCH_LIMIT: int = 50
    
    # ========== 匹配算法配置 ==========
    # 7维度权重
    WEIGHT_SKILLS: float = 0.25
    WEIGHT_EXPERIENCE: float = 0.20
    WEIGHT_SALARY: float = 0.15
    WEIGHT_LOCATION: float = 0.10
    WEIGHT_CULTURE: float = 0.10
    WEIGHT_GROWTH: float = 0.10
    WEIGHT_STABILITY: float = 0.10
    
    MATCH_THRESHOLD: float = 60.0  # 匹配阈值
    
    @property
    def DIMENSION_WEIGHTS(self) -> dict:
        """返回7维度权重字典"""
        return {
            "skills": self.WEIGHT_SKILLS,
            "experience": self.WEIGHT_EXPERIENCE,
            "salary": self.WEIGHT_SALARY,
            "location": self.WEIGHT_LOCATION,
            "culture": self.WEIGHT_CULTURE,
            "growth": self.WEIGHT_GROWTH,
            "stability": self.WEIGHT_STABILITY,
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # 允许额外字段


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（带缓存）"""
    return Settings()


# 导出配置实例
settings = get_settings()
