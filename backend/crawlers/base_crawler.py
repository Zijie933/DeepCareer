"""
基础爬虫类 - 所有爬虫的父类
"""
import asyncio
import random
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from fake_useragent import UserAgent
from backend.utils.logger import logger


class BaseCrawler(ABC):
    """爬虫基类"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = None
        self.page = None
        self.browser = None
        self.context = None
        
    def get_random_ua(self) -> str:
        """获取随机User-Agent"""
        return self.ua.random
    
    async def random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """随机延迟（反爬）"""
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"随机延迟 {delay:.2f} 秒")
        await asyncio.sleep(delay)
    
    async def scroll_page(self, times: int = 3):
        """滚动页面（加载动态内容）"""
        if not self.page:
            return
        
        for i in range(times):
            await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(random.uniform(0.5, 1.5))
    
    @abstractmethod
    async def search_jobs(
        self, 
        keyword: str, 
        city: str = "全国",
        page: int = 1
    ) -> List[Dict]:
        """
        搜索职位（子类必须实现）
        
        Args:
            keyword: 搜索关键词
            city: 城市
            page: 页码
        
        Returns:
            职位列表
        """
        pass
    
    @abstractmethod
    async def get_job_detail(self, job_url: str) -> Optional[Dict]:
        """
        获取职位详情（子类必须实现）
        
        Args:
            job_url: 职位URL
        
        Returns:
            职位详情
        """
        pass
    
    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
