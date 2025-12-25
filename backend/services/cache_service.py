"""
Redis 缓存服务
"""
import json
from typing import Any, Optional
import redis.asyncio as redis
from loguru import logger

from backend.config import settings


class CacheService:
    """Redis 缓存服务类"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.default_expire = settings.CACHE_EXPIRE_TIME
    
    async def connect(self):
        """连接 Redis"""
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            
            # 测试连接
            await self.redis_client.ping()
            logger.info("Redis 连接成功")
        
        except Exception as e:
            logger.error(f"Redis 连接失败: {str(e)}")
            raise
    
    async def close(self):
        """关闭 Redis 连接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis 连接已关闭")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值（自动反序列化 JSON）
        """
        try:
            value = await self.redis_client.get(key)
            
            if value is None:
                return None
            
            # 尝试解析 JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        except Exception as e:
            logger.error(f"Redis GET 失败 (key={key}): {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
    ) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值（自动序列化 JSON）
            expire: 过期时间（秒），None 表示使用默认值
        
        Returns:
            bool: 是否成功
        """
        try:
            # 序列化复杂对象
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            expire_time = expire if expire is not None else self.default_expire
            
            await self.redis_client.set(key, value, ex=expire_time)
            return True
        
        except Exception as e:
            logger.error(f"Redis SET 失败 (key={key}): {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否成功
        """
        try:
            await self.redis_client.delete(key)
            return True
        
        except Exception as e:
            logger.error(f"Redis DELETE 失败 (key={key}): {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在
        """
        try:
            return await self.redis_client.exists(key) > 0
        
        except Exception as e:
            logger.error(f"Redis EXISTS 失败 (key={key}): {str(e)}")
            return False
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """
        自增计数器
        
        Args:
            key: 缓存键
            amount: 增量
        
        Returns:
            int: 新值
        """
        try:
            return await self.redis_client.incrby(key, amount)
        
        except Exception as e:
            logger.error(f"Redis INCR 失败 (key={key}): {str(e)}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置过期时间
        
        Args:
            key: 缓存键
            seconds: 过期时间（秒）
        
        Returns:
            bool: 是否成功
        """
        try:
            return await self.redis_client.expire(key, seconds)
        
        except Exception as e:
            logger.error(f"Redis EXPIRE 失败 (key={key}): {str(e)}")
            return False
    
    def generate_key(self, prefix: str, *args) -> str:
        """
        生成缓存键
        
        Args:
            prefix: 前缀
            *args: 参数列表
        
        Returns:
            str: 缓存键 (格式: prefix:arg1:arg2:...)
        """
        parts = [prefix] + [str(arg) for arg in args]
        return ":".join(parts)


# 创建全局实例
cache_service = CacheService()
