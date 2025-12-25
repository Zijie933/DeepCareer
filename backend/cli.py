"""
DeepCareer 命令行工具
用法：deepcareer <command> [options]
"""
import argparse
import asyncio
import sys
import json
from pathlib import Path

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).parent.parent))


def crawl_command(args):
    """爬取职位命令"""
    from backend.crawlers.boss_web_crawler_playwright import BossWebCrawlerPlaywright
    from backend.config import settings
    from backend.utils.logger import setup_logger
    import logging
    
    setup_logger()
    logger = logging.getLogger(__name__)
    
    async def run_crawl():
        # 优先使用命令行参数，其次使用环境变量
        cookie = args.cookie or settings.BOSS_COOKIE
        
        if not cookie:
            logger.error("❌ 未配置Cookie，请通过以下方式之一设置：")
            logger.error("   1. 环境变量: export BOSS_COOKIE='your_cookie'")
            logger.error("   2. .env文件: BOSS_COOKIE=your_cookie")
            logger.error("   3. 命令行参数: --cookie 'your_cookie'")
            return []
        
        logger.info("=" * 70)
        logger.info(f"🚀 开始爬取 {args.city} - {args.keyword} （目标：{args.count}个）")
        logger.info("=" * 70)
        
        async with BossWebCrawlerPlaywright(
            min_delay=1.5,
            max_delay=3.0,
            headless=not args.visible,
            cookie_string=cookie,
            target_city=args.city
        ) as crawler:
            # 搜索职位
            all_jobs = await crawler.search_jobs(
                keyword=args.keyword,
                city=args.city,
                page=1,
                auto_scroll=False
            )
            
            if not all_jobs:
                logger.warning("未找到任何职位")
                return []
            
            logger.info(f"📋 找到 {len(all_jobs)} 个职位")
            
            # 获取详情
            jobs_to_fetch = all_jobs[:args.count]
            
            if args.detail:
                logger.info(f"📥 获取 {len(jobs_to_fetch)} 个职位详情（并发：{args.concurrent}）...")
                
                semaphore = asyncio.Semaphore(args.concurrent)
                
                async def fetch_detail(job, idx):
                    async with semaphore:
                        url = job.get("job_url")
                        if url:
                            detail = await crawler.get_job_detail(url, use_random_ua=True)
                            if detail:
                                job.update(detail)
                        return job
                
                jobs = await asyncio.gather(
                    *[fetch_detail(j, i) for i, j in enumerate(jobs_to_fetch, 1)],
                    return_exceptions=True
                )
                jobs = [j for j in jobs if not isinstance(j, Exception)]
            else:
                jobs = jobs_to_fetch
            
            # 保存结果
            output = args.output or f"{args.city}_{args.keyword}_jobs.json"
            with open(output, "w", encoding="utf-8") as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 成功爬取 {len(jobs)} 个职位，保存至: {output}")
            
            # 打印统计
            stats = crawler.get_stats()
            logger.info(f"📊 统计: 请求{stats['total_requests']}次, 成功率{stats['success_rate']}")
            
            return jobs
    
    asyncio.run(run_crawl())


def serve_command(args):
    """启动API服务"""
    import uvicorn
    from backend.config import settings
    
    print(f"🚀 启动DeepCareer API服务...")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   文档: http://{args.host}:{args.port}/docs")
    
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


def cities_command(args):
    """列出支持的城市"""
    from backend.crawlers.boss_web_crawler_playwright import BossWebCrawlerPlaywright
    
    print("📍 支持的城市列表：")
    print("-" * 40)
    for city, code in BossWebCrawlerPlaywright.CITY_CODES.items():
        print(f"  {city}: {code}")


def version_command(args):
    """显示版本信息"""
    print("DeepCareer v1.0.0")
    print("智能职位匹配系统")


def frontend_command(args):
    """启动前端开发服务"""
    import subprocess
    import os
    
    frontend_dir = Path(__file__).parent.parent / "frontend"
    
    if not frontend_dir.exists():
        print("❌ 前端目录不存在")
        return
    
    os.chdir(frontend_dir)
    
    if args.install:
        print("📦 安装前端依赖...")
        subprocess.run(["npm", "install"], check=True)
    
    print("🚀 启动前端开发服务...")
    print("   地址: http://localhost:3000")
    subprocess.run(["npm", "run", "dev"])


def dev_command(args):
    """同时启动前后端开发服务"""
    import subprocess
    import os
    import signal
    import time
    
    project_dir = Path(__file__).parent.parent
    frontend_dir = project_dir / "frontend"
    
    if not frontend_dir.exists():
        print("❌ 前端目录不存在")
        return
    
    processes = []
    
    def cleanup(signum=None, frame=None):
        print("\n🛑 正在关闭服务...")
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=3)
            except:
                p.kill()
        print("✅ 服务已关闭")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # 启动后端
        print("🚀 启动后端API服务...")
        print(f"   地址: http://localhost:{args.backend_port}")
        print(f"   文档: http://localhost:{args.backend_port}/docs")
        
        backend_cmd = [
            sys.executable, "-m", "uvicorn", "backend.main:app",
            "--host", "0.0.0.0",
            "--port", str(args.backend_port)
        ]
        if args.reload:
            backend_cmd.append("--reload")
        
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE if args.quiet else None,
            stderr=subprocess.STDOUT if args.quiet else None
        )
        processes.append(backend_proc)
        
        # 等待后端启动（检测健康检查接口）
        import urllib.request
        print("⏳ 等待后端启动...")
        for i in range(30):  # 最多等30秒
            try:
                urllib.request.urlopen(f"http://localhost:{args.backend_port}/health", timeout=1)
                print("✅ 后端已就绪")
                break
            except:
                time.sleep(1)
        else:
            print("⚠️ 后端启动超时，继续启动前端...")
        
        # 启动前端
        print("🎨 启动前端开发服务...")
        print(f"   地址: http://localhost:{args.frontend_port}")
        
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(args.frontend_port)],
            cwd=frontend_dir,
            stdout=subprocess.PIPE if args.quiet else None,
            stderr=subprocess.STDOUT if args.quiet else None
        )
        processes.append(frontend_proc)
        
        print("\n" + "=" * 50)
        print("✅ DeepCareer 开发环境已启动!")
        print(f"   前端: http://localhost:{args.frontend_port}")
        print(f"   后端: http://localhost:{args.backend_port}")
        print(f"   文档: http://localhost:{args.backend_port}/docs")
        print("=" * 50)
        print("按 Ctrl+C 停止所有服务\n")
        
        # 等待进程
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(f"⚠️ 服务异常退出 (code={p.returncode})")
                    cleanup()
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        cleanup()


def main():
    """CLI主入口"""
    parser = argparse.ArgumentParser(
        prog="deepcareer",
        description="DeepCareer - 智能职位匹配系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  deepcareer crawl --city 深圳 --keyword Python --count 10
  deepcareer serve --port 8001
  deepcareer cities
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # ========== crawl 命令 ==========
    crawl_parser = subparsers.add_parser("crawl", help="爬取BOSS直聘职位")
    crawl_parser.add_argument("--city", "-c", type=str, required=True,
                              help="城市名称（如：北京、上海、深圳）")
    crawl_parser.add_argument("--keyword", "-k", type=str, required=True,
                              help="搜索关键词（如：Python、Java）")
    crawl_parser.add_argument("--count", "-n", type=int, default=10,
                              help="爬取数量（默认：10）")
    crawl_parser.add_argument("--output", "-o", type=str, default=None,
                              help="输出文件名")
    crawl_parser.add_argument("--concurrent", type=int, default=5,
                              help="并发数（默认：5）")
    crawl_parser.add_argument("--cookie", type=str, default=None,
                              help="BOSS直聘Cookie")
    crawl_parser.add_argument("--no-detail", dest="detail", action="store_false",
                              help="不获取详情页")
    crawl_parser.add_argument("--visible", action="store_true",
                              help="显示浏览器窗口")
    crawl_parser.set_defaults(func=crawl_command, detail=True)
    
    # ========== serve 命令 ==========
    serve_parser = subparsers.add_parser("serve", help="启动API服务")
    serve_parser.add_argument("--host", "-H", type=str, default="0.0.0.0",
                              help="监听地址（默认：0.0.0.0）")
    serve_parser.add_argument("--port", "-p", type=int, default=8001,
                              help="监听端口（默认：8001）")
    serve_parser.add_argument("--reload", "-r", action="store_true",
                              help="开发模式（自动重载）")
    serve_parser.set_defaults(func=serve_command)
    
    # ========== cities 命令 ==========
    cities_parser = subparsers.add_parser("cities", help="列出支持的城市")
    cities_parser.set_defaults(func=cities_command)
    
    # ========== version 命令 ==========
    version_parser = subparsers.add_parser("version", help="显示版本信息")
    version_parser.set_defaults(func=version_command)
    
    # ========== frontend 命令 ==========
    frontend_parser = subparsers.add_parser("frontend", help="启动前端开发服务")
    frontend_parser.add_argument("--install", "-i", action="store_true",
                                  help="先安装依赖")
    frontend_parser.set_defaults(func=frontend_command)
    
    # ========== dev 命令 ==========
    dev_parser = subparsers.add_parser("dev", help="同时启动前后端开发服务")
    dev_parser.add_argument("--frontend-port", "-f", type=int, default=3000,
                            help="前端端口（默认：3000）")
    dev_parser.add_argument("--backend-port", "-b", type=int, default=8001,
                            help="后端端口（默认：8001）")
    dev_parser.add_argument("--reload", "-r", action="store_true",
                            help="后端自动重载")
    dev_parser.add_argument("--quiet", "-q", action="store_true",
                            help="静默模式（隐藏子进程输出）")
    dev_parser.set_defaults(func=dev_command)
    
    # 解析参数
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    # 执行命令
    args.func(args)


if __name__ == "__main__":
    main()
