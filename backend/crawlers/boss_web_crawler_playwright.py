"""
BOSS直聘网页爬虫 - 基于Playwright（无需Cookie，多UA轮换）
"""
import asyncio
import random
import time
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
from backend.utils.logger import logger


class UserAgentPool:
    """User-Agent池（包含主流浏览器的真实UA）"""
    
    USER_AGENTS = [
        # Chrome (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Chrome (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Firefox (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        
        # Firefox (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        
        # Safari (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        
        # Edge (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    
    @classmethod
    def get_random(cls) -> str:
        """获取随机UA"""
        return random.choice(cls.USER_AGENTS)


class RateLimiter:
    """请求限流器"""
    
    def __init__(self, min_interval: float = 3.0, max_interval: float = 8.0):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.last_request_time = 0
        self._lock = asyncio.Lock()
    
    async def wait(self):
        """等待到可以发送下一个请求"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request_time
            
            required_wait = random.uniform(self.min_interval, self.max_interval)
            wait_time = max(0, required_wait - elapsed)
            
            if wait_time > 0:
                logger.debug(f"⏱️  限流等待 {wait_time:.2f} 秒...")
                await asyncio.sleep(wait_time)
            
            self.last_request_time = time.time()


class BossWebCrawlerPlaywright:
    """BOSS直聘网页爬虫（Playwright版，无需Cookie，多UA轮换）"""
    
    BASE_URL = "https://www.zhipin.com"
    SEARCH_URL = "https://www.zhipin.com/web/geek/jobs"
    
    CITY_CODES = {
        # 全国
        "全国": "100010000",
        
        # 一线城市
        "北京": "101010100",
        "上海": "101020100",
        "广州": "101280100",
        "深圳": "101280600",
        
        # 新一线城市
        "杭州": "101210100",
        "成都": "101270100",
        "重庆": "101040100",
        "武汉": "101200100",
        "西安": "101110100",
        "苏州": "101190400",
        "南京": "101190100",
        "天津": "101030100",
        "郑州": "101180100",
        "长沙": "101250100",
        "东莞": "101281600",
        "佛山": "101280800",
        "宁波": "101210400",
        "青岛": "101120200",
        "沈阳": "101070100",
        
        # 二线城市
        "合肥": "101220100",
        "厦门": "101230200",
        "无锡": "101190200",
        "昆明": "101290100",
        "大连": "101070200",
        "福州": "101230100",
        "哈尔滨": "101050100",
        "济南": "101120100",
        "温州": "101210700",
        "石家庄": "101090100",
        "南宁": "101300100",
        "长春": "101060100",
        "泉州": "101230500",
        "贵阳": "101260100",
        "南昌": "101240100",
        "金华": "101210900",
        "常州": "101191100",
        "珠海": "101280700",
        "惠州": "101280300",
        "嘉兴": "101210300",
        "南通": "101190500",
        "中山": "101281700",
        "太原": "101100100",
        "兰州": "101160100",
        "徐州": "101190800",
        "台州": "101210600",
        "绍兴": "101210500",
        "烟台": "101120500",
        "海口": "101310100",
        
        # 其他城市
        "乌鲁木齐": "101130100",
        "呼和浩特": "101080100",
        "银川": "101170100",
        "西宁": "101150100",
        "拉萨": "101140100",
        "三亚": "101310200",
    }
    
    def __init__(
        self,
        min_delay: float = 3.0,
        max_delay: float = 8.0,
        max_retries: int = 3,
        retry_backoff: float = 15.0,
        timeout: float = 30000,  # Playwright使用毫秒
        headless: bool = True,
        cookie_string: Optional[str] = None,  # Cookie字符串
        target_city: Optional[str] = None  # 新增：目标城市（用于替换Cookie中的lastCity）
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.timeout = timeout
        self.headless = headless
        self.cookie_string = cookie_string
        self.target_city = target_city
        
        self.rate_limiter = RateLimiter(min_delay, max_delay)
        
        self.playwright = None
        self.browser = None
        self.context = None
        
        self.stats = {
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0,
            "retried_requests": 0,
            "user_agents_used": set(),
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 创建上下文（随机UA）
        user_agent = UserAgentPool.get_random()
        self.stats["user_agents_used"].add(user_agent)
        
        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN'
        )
        
        # 如果提供了Cookie，则设置Cookie
        if self.cookie_string:
            # 如果指定了目标城市，替换lastCity
            target_city_code = None
            if self.target_city and self.target_city in self.CITY_CODES:
                target_city_code = self.CITY_CODES[self.target_city]
                logger.info(f"🔄 将Cookie中的lastCity替换为: {self.target_city} ({target_city_code})")
            
            cookies = self._parse_cookie_string(self.cookie_string, target_city_code)
            await self.context.add_cookies(cookies)
            logger.info(f"🍪 已设置 {len(cookies)} 个Cookie")
        
        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info(f"🌐 浏览器已启动 (UA: {user_agent[:50]}...)")
        return self
    
    def _parse_cookie_string(self, cookie_string: str, target_city_code: Optional[str] = None) -> List[Dict]:
        """
        解析Cookie字符串为Playwright格式
        
        Args:
            cookie_string: Cookie字符串
            target_city_code: 目标城市代码，如果提供则替换lastCity
        
        Returns:
            Cookie字典列表
        """
        cookies = []
        for item in cookie_string.split('; '):
            if '=' in item:
                name, value = item.split('=', 1)
                
                # 如果指定了目标城市代码，替换lastCity
                if name == 'lastCity' and target_city_code:
                    value = target_city_code
                
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.zhipin.com',
                    'path': '/'
                })
        
        return cookies
    
    def update_cookie_city(self, city: str):
        """
        更新Cookie中的lastCity为目标城市
        
        Args:
            city: 城市名称
        """
        if not self.cookie_string:
            return
        
        city_code = self.CITY_CODES.get(city)
        if not city_code:
            logger.warning(f"未找到城市 {city} 的代码")
            return
        
        # 替换Cookie中的lastCity
        import re
        self.cookie_string = re.sub(
            r'lastCity=\d+',
            f'lastCity={city_code}',
            self.cookie_string
        )
        logger.info(f"🔄 已更新Cookie中的lastCity为: {city_code}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        logger.info(f"🔒 浏览器已关闭 - 统计: {self.get_stats()}")
    
    async def _parse_job_cards(self, page: Page) -> List[Dict]:
        """
        解析职位卡片（列表页）
        
        根据实际HTML结构：
        - ul.rec-job-list: 职位列表容器
        - li.job-card-box: 每个职位卡片
        - .job-info > .job-title > a.job-name: 职位名称和链接
        - .job-salary: 薪资
        - .tag-list > li: 经验、学历等标签
        - .job-card-footer: 公司信息
        
        Args:
            page: Playwright页面对象
        
        Returns:
            职位列表（基础信息+详情页链接）
        """
        jobs = []
        
        try:
            # 等待职位列表加载
            await page.wait_for_selector('ul.rec-job-list', timeout=15000)
            logger.debug("✅ 职位列表已加载")
            
            # 获取所有职位卡片
            job_cards = await page.query_selector_all('li.job-card-box')
            
            logger.info(f"📋 找到 {len(job_cards)} 个职位卡片")
            
            for idx, card in enumerate(job_cards, 1):
                try:
                    # 1. 职位名称和链接（在 .job-info > .job-title > a.job-name）
                    job_name_link = await card.query_selector('a.job-name')
                    if not job_name_link:
                        logger.debug(f"⚠️  卡片 {idx} 无 job-name 链接，跳过")
                        continue
                    
                    title = await job_name_link.text_content()
                    href = await job_name_link.get_attribute('href')
                    
                    if not href:
                        logger.debug(f"⚠️  卡片 {idx} href为空，跳过")
                        continue
                    
                    # 构建完整URL
                    job_url = self.BASE_URL + href if not href.startswith('http') else href
                    
                    # 提取job_id
                    job_id = ""
                    parts = href.split('/')
                    if len(parts) > 0:
                        job_id = parts[-1].replace('.html', '').split('?')[0]
                    
                    # 2. 薪资
                    salary_elem = await card.query_selector('.job-salary')
                    salary = await salary_elem.text_content() if salary_elem else ""
                    
                    # 3. 标签（经验、学历等）
                    tag_list = await card.query_selector_all('ul.tag-list > li')
                    tags = []
                    for tag_elem in tag_list:
                        tag_text = await tag_elem.text_content()
                        if tag_text:
                            tags.append(tag_text.strip())
                    
                    # 解析标签（通常第一个是经验，第二个是学历）
                    experience = tags[0] if len(tags) > 0 else "经验不限"
                    education = tags[1] if len(tags) > 1 else "学历不限"
                    
                    # 4. 公司信息（在 .job-card-footer）
                    footer = await card.query_selector('.job-card-footer')
                    company = ""
                    location = ""
                    
                    if footer:
                        # 公司简称（从 .boss-name 提取，详情页会用更准确的值覆盖）
                        company_elem = await footer.query_selector('.boss-name')
                        if company_elem:
                            company = await company_elem.text_content()
                        
                        # 工作地点
                        location_elem = await footer.query_selector('.company-location')
                        if location_elem:
                            location = await location_elem.text_content()
                    
                    job_data = {
                        "job_id": job_id,
                        "title": title.strip() if title else "",
                        "company": company.strip() if company else "",
                        "salary": salary.strip() if salary else "",
                        "location": location.strip() if location else "",
                        "experience": experience,
                        "education": education,
                        "tags": tags,
                        "job_url": job_url,
                        "platform": "boss",
                    }
                    
                    jobs.append(job_data)
                    logger.debug(f"✅ 解析职位 {idx}: {job_data['title']} @ {job_data['company']}")
                
                except Exception as e:
                    logger.error(f"❌ 解析职位卡片 {idx} 失败: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"❌ 等待职位列表超时或解析失败: {e}")
            # 保存截图和HTML用于调试
            try:
                await page.screenshot(path="debug_list_page.png")
                html_content = await page.content()
                with open("debug_list_page.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info("💾 调试文件已保存: debug_list_page.png 和 debug_list_page.html")
            except:
                pass
        
        return jobs
    
    async def search_jobs(
        self,
        keyword: str,
        city: str = "深圳",
        page: int = 1,
        auto_scroll: bool = True,
        max_scroll: int = 5
    ) -> List[Dict]:
        """
        搜索职位（使用Playwright渲染页面）
        
        Args:
            keyword: 搜索关键词
            city: 城市名称
            page: 页码
            auto_scroll: 是否自动滚动加载更多（需要Cookie支持）
            max_scroll: 最大滚动次数
        
        Returns:
            职位列表
        """
        city_code = self.CITY_CODES.get(city, self.CITY_CODES["深圳"])
        
        url = f"{self.SEARCH_URL}?query={keyword}&city={city_code}&page={page}"
        
        logger.info(f"🔍 搜索职位: keyword={keyword}, city={city}, page={page}")
        
        try:
            # 限流等待
            await self.rate_limiter.wait()
            
            self.stats["total_requests"] += 1
            
            # 创建新页面
            page_obj = await self.context.new_page()
            
            try:
                # 访问页面
                logger.info(f"🌐 访问: {url}")
                await page_obj.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                
                # 等待JavaScript渲染
                logger.debug("⏱️  等待页面渲染...")
                await asyncio.sleep(random.uniform(3, 5))
                
                # 如果启用自动滚动且有Cookie
                if auto_scroll and self.cookie_string:
                    try:
                        initial_count = len(await page_obj.query_selector_all('li.job-card-box'))
                        logger.info(f"📜 开始滚动加载更多职位（初始: {initial_count}）...")
                        
                        for i in range(max_scroll):
                            # 检查页面是否仍然有效
                            if page_obj.is_closed():
                                logger.warning("⚠️ 页面已关闭，停止滚动")
                                break
                            
                            await page_obj.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                            await asyncio.sleep(random.uniform(1.5, 2.5))
                            
                            # 检查是否发生导航
                            if page_obj.is_closed():
                                logger.warning("⚠️ 页面在滚动后关闭，停止滚动")
                                break
                            
                            try:
                                current_count = len(await page_obj.query_selector_all('li.job-card-box'))
                                if current_count > initial_count:
                                    logger.debug(f"  滚动 {i+1}/{max_scroll}: 新增 {current_count - initial_count} 个职位")
                                    initial_count = current_count
                                else:
                                    logger.debug(f"  滚动 {i+1}/{max_scroll}: 没有新增职位")
                            except Exception as scroll_err:
                                logger.warning(f"⚠️ 滚动时出错: {scroll_err}，停止滚动")
                                break
                    except Exception as scroll_init_err:
                        logger.warning(f"⚠️ 初始化滚动失败: {scroll_init_err}，跳过滚动")
                
                # 解析职位
                jobs = await self._parse_job_cards(page_obj)
                
                self.stats["success_requests"] += 1
                logger.info(f"✅ 成功解析 {len(jobs)} 个职位")
                
                return jobs
            
            finally:
                await page_obj.close()
        
        except Exception as e:
            logger.error(f"❌ 搜索职位失败: {e}")
            self.stats["failed_requests"] += 1
            return []
    
    async def get_job_detail(self, job_url: str, use_random_ua: bool = False) -> Optional[Dict]:
        """
        获取职位详情页的完整信息
        
        根据HTML结构：
        - job-primary detail-box: 招聘岗位基本信息（岗位名、工资、学历等）
        - job-detail-section: 职位描述区域
          - job-sec-text: 职位描述文本
          - job-keyword-list: 职位标签
        - job-detail-section job-detail-company: 公司信息
          - detail-section-item company-info-box: 公司介绍
          - detail-section-item company-address: 工作地址
        
        Args:
            job_url: 职位详情URL
            use_random_ua: 是否为此请求使用随机User-Agent（用于并发时减少特征）
        
        Returns:
            职位详情字典
        """
        # logger.debug(f"📄 获取职位详情: {job_url}")
        
        try:
            # 限流等待
            await self.rate_limiter.wait()
            
            self.stats["total_requests"] += 1
            
            # 如果启用随机UA，创建新的context
            if use_random_ua:
                user_agent = UserAgentPool.get_random()
                self.stats["user_agents_used"].add(user_agent)
                
                # 创建临时context
                temp_context = await self.browser.new_context(
                    user_agent=user_agent,
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN'
                )
                
                # 如果有Cookie，也设置到临时context
                if self.cookie_string:
                    target_city_code = None
                    if self.target_city and self.target_city in self.CITY_CODES:
                        target_city_code = self.CITY_CODES[self.target_city]
                    cookies = self._parse_cookie_string(self.cookie_string, target_city_code)
                    await temp_context.add_cookies(cookies)
                
                # 注入反检测脚本
                await temp_context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                page = await temp_context.new_page()
                should_close_context = True
            else:
                page = await self.context.new_page()
                temp_context = None
                should_close_context = False
            
            try:
                await page.goto(job_url, wait_until='domcontentloaded', timeout=self.timeout)
                
                # 等待详情页加载
                await page.wait_for_selector('.job-primary', timeout=15000)
                logger.debug("✅ 职位详情页已加载")
                
                # 额外等待JS渲染
                await asyncio.sleep(random.uniform(2, 4))
                
                detail = {}
                
                # ========== 1. 职位基本信息（job-primary）==========
                primary_section = await page.query_selector('.job-primary')
                if primary_section:
                    # 职位名称（h1标签）
                    title_h1 = await primary_section.query_selector('.name h1')
                    if title_h1:
                        detail['job_title'] = (await title_h1.text_content()).strip()
                    
                    # 薪资（独立的.salary元素）
                    salary_elem = await primary_section.query_selector('.salary')
                    if salary_elem:
                        detail['salary_detail'] = (await salary_elem.text_content()).strip()
                    
                    # 标签信息（分别提取地区、经验、学历）
                    # 地区
                    city_elem = await primary_section.query_selector('.text-desc.text-city')
                    if city_elem:
                        detail['work_city'] = (await city_elem.text_content()).strip()
                    
                    # 经验（注意拼写是experiece不是experience）
                    exp_elem = await primary_section.query_selector('.text-desc.text-experiece')
                    if exp_elem:
                        detail['experience_requirement'] = (await exp_elem.text_content()).strip()
                    
                    # 学历
                    degree_elem = await primary_section.query_selector('.text-desc.text-degree')
                    if degree_elem:
                        detail['education_requirement'] = (await degree_elem.text_content()).strip()
                
                # ========== 2. 职位描述（job-detail-section）==========
                # 职位描述文本
                job_desc_elem = await page.query_selector('.job-sec-text')
                if job_desc_elem:
                    desc_text = await job_desc_elem.text_content()
                    detail['job_description'] = desc_text.strip() if desc_text else ""
                else:
                    detail['job_description'] = ""
                
                # 职位标签/关键词
                keyword_list = await page.query_selector_all('.job-keyword-list > li')
                keywords = []
                for kw in keyword_list:
                    kw_text = await kw.text_content()
                    if kw_text:
                        keywords.append(kw_text.strip())
                detail['job_keywords'] = keywords
                
                # ========== 3. 公司信息（job-detail-company）==========
                company_section = await page.query_selector('.job-detail-company')
                if company_section:
                    # 公司简称（从 ka="job-detail-company_custompage" 提取，覆盖列表页的值）
                    company_short_elem = await company_section.query_selector('[ka="job-detail-company_custompage"]')
                    if company_short_elem:
                        detail['company'] = (await company_short_elem.text_content()).strip()
                    
                    # 公司全称（从工商信息的 li.company-name 提取）
                    business_info_box = await company_section.query_selector('.business-info-box')
                    if business_info_box:
                        company_name_li = await business_info_box.query_selector('li.company-name')
                        if company_name_li:
                            # 获取完整文本，然后移除"公司名称"标签
                            full_text = (await company_name_li.text_content()).strip()
                            # 移除"公司名称"标签文字
                            detail['company_name'] = full_text.replace('公司名称', '').strip()
                    
                    # 公司介绍（company-info-box）
                    company_info_box = await company_section.query_selector('.company-info-box')
                    if company_info_box:
                        company_intro = await company_info_box.query_selector('.content')
                        if company_intro:
                            detail['company_intro'] = (await company_intro.text_content()).strip()
                    
                    # 工作地址（company-address）
                    address_box = await company_section.query_selector('.company-address')
                    if address_box:
                        address_text = await address_box.query_selector('.location-address')
                        if address_text:
                            detail['work_address'] = (await address_text.text_content()).strip()
                
                self.stats["success_requests"] += 1
                # logger.debug(f"✅ 详情获取成功 - {detail.get('job_title', 'N/A')}")
                
                return detail
            
            except asyncio.TimeoutError:
                logger.error(f"❌ 详情页加载超时: {job_url}")
                self.stats["failed_requests"] += 1
                return None
            
            finally:
                await page.close()
                if should_close_context and temp_context:
                    await temp_context.close()
        
        except Exception as e:
            logger.error(f"❌ 获取职位详情失败: {e}", exc_info=True)
            self.stats["failed_requests"] += 1
            return None
    
    async def search_and_get_details(
        self,
        keyword: str,
        city: str = "深圳",
        page: int = 1,
        max_results: int = 10,
        max_concurrent: int = 5,  # 增加默认并发数到5
        use_random_ua: bool = True  # 默认启用随机UA
    ) -> List[Dict]:
        """
        搜索并获取详情
        
        Args:
            keyword: 搜索关键词
            city: 城市
            page: 页码
            max_results: 最多获取数量
            max_concurrent: 最大并发数
            use_random_ua: 是否为每个详情请求使用随机User-Agent
        
        Returns:
            包含完整信息的职位列表
        """
        # 1. 搜索职位（只搜索一次）
        jobs = await self.search_jobs(keyword, city, page)
        
        if not jobs:
            return []
        
        # 限制数量
        jobs = jobs[:max_results]
        
        # 2. 获取详情（使用信号量控制并发）
        logger.info(f"📥 开始获取 {len(jobs)} 个职位的详情（并发数: {max_concurrent}, 随机UA: {use_random_ua}）...")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_detail_with_limit(job: Dict, index: int) -> Dict:
            """带限流的详情获取"""
            async with semaphore:
                job_url = job.get("job_url", "")
                if not job_url:
                    return job
                
                logger.info(f"  [{index}/{len(jobs)}] {job.get('title', 'N/A')}")
                
                detail = await self.get_job_detail(job_url, use_random_ua=use_random_ua)
                
                if detail:
                    job.update(detail)
                
                return job
        
        # 并发获取详情
        jobs_with_details = await asyncio.gather(
            *[fetch_detail_with_limit(job, idx) for idx, job in enumerate(jobs, 1)],
            return_exceptions=True
        )
        
        # 过滤异常结果
        valid_jobs = [
            job for job in jobs_with_details 
            if not isinstance(job, Exception)
        ]
        
        logger.info(f"✅ 成功获取 {len(valid_jobs)}/{len(jobs)} 个职位的完整信息")
        return valid_jobs
    
    def get_stats(self) -> Dict:
        """获取爬虫统计信息"""
        success_rate = (
            self.stats["success_requests"] / self.stats["total_requests"] * 100
            if self.stats["total_requests"] > 0
            else 0
        )
        
        return {
            "total_requests": self.stats["total_requests"],
            "success_requests": self.stats["success_requests"],
            "failed_requests": self.stats["failed_requests"],
            "retried_requests": self.stats["retried_requests"],
            "success_rate": f"{success_rate:.2f}%",
            "unique_user_agents": len(self.stats["user_agents_used"]),
        }
